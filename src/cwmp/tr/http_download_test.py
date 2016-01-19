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

# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for http_download.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

from collections import namedtuple  #pylint: disable-msg=C6202
import shutil
import tempfile
import unittest

import google3
import http_download


mock_http_clients = []


class MockHttpClient(object):
  def __init__(self, io_loop=None):
    self.did_fetch = False
    self.request = None
    self.callback = None
    mock_http_clients.append(self)

  def fetch(self, request, callback):
    self.did_fetch = True
    self.request = request
    self.callback = callback


class MockHttpResponse(object):
  def __init__(self, errorcode):
    self.error = namedtuple('error', 'code')
    self.error.code = errorcode
    self.headers = []


class MockIoloop(object):
  def __init__(self):
    self.time = None
    self.callback = None

  def add_timeout(self, time, callback):
    self.time = time
    self.callback = callback


class HttpDownloadTest(unittest.TestCase):
  """tests for http_download.py HttpDownload."""

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    http_download.HTTPCLIENT = MockHttpClient
    self.dl_cb_faultcode = None
    self.dl_cb_faultstring = None
    del mock_http_clients[:]

  def tearDown(self):
    shutil.rmtree(self.tmpdir)
    del mock_http_clients[:]

  def testDigest(self):
    expected = '6629fae49393a05397450978507c4ef1'
    actual = http_download.calc_http_digest(
        'GET',
        '/dir/index.html',
        'auth',
        nonce='dcd98b7102dd2f0e8b11d0f600bfb0c093',
        cnonce='0a4f113b',
        nc='00000001',
        username='Mufasa',
        password='Circle Of Life',
        realm='testrealm@host.com')
    self.assertEqual(expected, actual)

  def downloadCallback(self, faultcode, faultstring, filename):
    self.dl_cb_faultcode = faultcode
    self.dl_cb_faultstring = faultstring
    self.dl_cb_filename = filename

  def testFetch(self):
    ioloop = MockIoloop()
    username = 'uname'
    password = 'pword'
    url = 'scheme://host:port/'
    dl = http_download.HttpDownload(url, username=username, password=password,
                                    download_complete_cb=self.downloadCallback,
                                    ioloop=ioloop)
    dl.fetch()
    self.assertEqual(len(mock_http_clients), 1)
    ht = mock_http_clients[0]
    self.assertTrue(ht.did_fetch)
    self.assertTrue(ht.request is not None)
    self.assertEqual(ht.request.auth_username, username)
    self.assertEqual(ht.request.auth_password, password)
    self.assertEqual(ht.request.url, url)

    resp = MockHttpResponse(418)
    ht.callback(resp)
    self.assertEqual(self.dl_cb_faultcode, 9010)  # DOWNLOAD_FAILED
    self.assertTrue(self.dl_cb_faultstring)
    self.assertFalse(self.dl_cb_filename)


if __name__ == '__main__':
  unittest.main()
