#!/usr/bin/python
# Copyright 2011 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Handlers for tr-69 Download and Scheduled Download."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import hashlib
import json
import os
import random
import sys
import tempfile

import google3
import helpers
import tornado
import tornado.httpclient
import tornado.ioloop
import tornado.web

from src.logger.HoneythingLogging import HTLogging

ht = HTLogging()

# Unit tests can override this to pass in a mock
HTTPCLIENT = tornado.httpclient.AsyncHTTPClient

# tr-69 fault codes
DOWNLOAD_FAILED = 9010


def _uri_path(url):
  pos = url.find('://')
  if pos >= 0:
    url = url[pos+3:]
  pos = url.find('/')
  if pos >= 0:
    url = url[pos:]
  return url


def calc_http_digest(method, uripath, qop, nonce, cnonce, nc,
                     username, realm, password):
  def H(s):
    return hashlib.md5(s).hexdigest()
  def KD(secret, data):
    return H(secret + ':' + data)
  A1 = username + ':' + realm + ':' + password
  A2 = method + ':' + uripath
  digest = KD(H(A1), nonce + ':' + nc + ':' + cnonce + ':' + qop + ':' + H(A2))
  return digest


class HttpDownload(object):
  def __init__(self, url, username=None, password=None,
               download_complete_cb=None, ioloop=None, download_dir=None):
    self.url = str(url)
    self.username = str(username)
    self.password = str(password)
    self.download_complete_cb = download_complete_cb
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.download_dir = download_dir

  def fetch(self):
    """Begin downloading file."""
    self.auth_header = None
    self.tempfile = None
    return self._start_download()

  def _start_download(self):
    #print 'starting (auth_header=%r)' % self.auth_header
    ht.logger.info('starting (auth_header=%r)' % self.auth_header)
    if not self.tempfile:
      self.tempfile = tempfile.NamedTemporaryFile(delete=True,
                                                  dir=self.download_dir)
    kwargs = dict(url=self.url,
                  request_timeout=3600.0,
                  streaming_callback=self.tempfile.write,
                  use_gzip=True, allow_ipv6=True,
                  user_agent='tr69-cpe-agent')
    if self.auth_header:
      kwargs.update(dict(headers=dict(Authorization=self.auth_header)))
    elif self.username and self.password:
      kwargs.update(dict(auth_username=self.username,
                         auth_password=self.password))
    req = tornado.httpclient.HTTPRequest(**kwargs)
    self.http_client = HTTPCLIENT(io_loop=self.ioloop)
    self.http_client.fetch(req, self._async_fetch_callback)

  def _calculate_auth_header(self, response):
    """HTTP Digest Authentication."""
    h = response.headers.get('www-authenticate', None)
    if not h:
      return
    authtype, paramstr = h.split(' ', 1)
    if authtype != 'Digest':
      return

    params = {}
    for param in paramstr.split(','):
      name, value = param.split('=')
      assert(value.startswith('"') and value.endswith('"'))
      params[name] = value[1:-1]

    uripath = _uri_path(self.url)
    nc = '00000001'
    nonce = params['nonce']
    realm = params['realm']
    opaque = params.get('opaque', None)
    cnonce = str(random.getrandbits(32))
    username = self.username
    password = self.password
    qop = 'auth'
    returns = dict(uri=uripath,
                   qop=qop,
                   nc=nc,
                   cnonce=cnonce,
                   nonce=nonce,
                   username=username,
                   realm=realm)
    if opaque:
      returns['opaque'] = opaque
    returns['response'] = calc_http_digest(method='GET',
                                           uripath=uripath,
                                           qop=qop,
                                           nonce=nonce,
                                           cnonce=cnonce,
                                           nc=nc,
                                           username=username,
                                           realm=realm,
                                           password=password)

    returnlist = [('%s="%s"' % (k, v)) for k, v in returns.items()]
    return 'Digest %s' % ','.join(returnlist)

  def _async_fetch_callback(self, response):
    """Called for each chunk of data downloaded."""
    if (response.error and response.error.code == 401 and
        not self.auth_header and self.username and self.password):
      #print '401 error, attempting Digest auth'
      ht.logger.info('401 error, attempting Digest auth')
      self.auth_header = self._calculate_auth_header(response)
      if self.auth_header:
        self._start_download()
        return

    self.tempfile.flush()

    if response.error:
      #print('Download failed: {0!r}'.format(response.error))
      #print json.dumps(response.headers, indent=2)
      ht.logger.info('Download failed: {0!r}'.format(response.error))
      ht.logger.info(json.dumps(response.headers, indent=2))
      self.tempfile.close()
      self.download_complete_cb(
          DOWNLOAD_FAILED,
          'Download failed {0!s}'.format(response.error.code),
          None)
    else:
      self.download_complete_cb(0, '', self.tempfile)
      #print('Download success: {0}'.format(self.tempfile.name))
      ht.logger.info('Download success: {0}'.format(self.tempfile.name))


def main():
  ioloop = tornado.ioloop.IOLoop.instance()
  dl = HttpDownload(ioloop)
  url = len(sys.argv) > 1 and sys.argv[1] or 'http://www.google.com/'
  username = len(sys.argv) > 2 and sys.argv[2]
  password = len(sys.argv) > 3 and sys.argv[3]
  #print 'using URL: %s' % url
  ht.logger.info('using URL: %s' % url)
  dl.download(url=url, username=username, password=password, delay_seconds=0)
  ioloop.start()

if __name__ == '__main__':
  main()
