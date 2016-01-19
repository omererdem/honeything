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

# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#pylint: disable-msg=W0404
#
"""Implement the TR-069 CWMP Sesion handling."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import functools
import tornado.httpclient
import tornado.ioloop

# SPEC3 = TR-069_Amendment-3.pdf
# http://www.broadband-forum.org/technical/download/TR-069_Amendment-3.pdf

graphviz = r"""
digraph DLstates {
  node [shape=box]

  CONNECT [label="CONNECT"]
  ACTIVE [label="ACTIVE\nsend responses or requests"]
  ONHOLD [label="ONHOLD\nsend responses"]
  NOMORE [label="NOMORE\nsend responses"]
  DONE [label="DONE\nclose session"]

  CONNECT -> ACTIVE [label="Send Inform"]
  ACTIVE -> ONHOLD [label="onhold=True"]
  ONHOLD -> ACTIVE [label="onhold=False"]
  ACTIVE -> NOMORE [label="send empty POST"]
  NOMORE -> DONE [label="receive empty Body"]
}
"""

HTTPCLIENT = tornado.httpclient.AsyncHTTPClient


class CwmpSession(object):
  """State machine to handle the lifecycle of a TCP session with the ACS."""

  CONNECT = 'CONNECT'
  ACTIVE = 'ACTIVE'
  ONHOLD = 'ONHOLD'
  NOMORE = 'NOMORE'
  DONE = 'DONE'

  def __init__(self, acs_url, ioloop=None):
    self.http = HTTPCLIENT(max_simultaneous_connections=1,
                           io_loop=ioloop or tornado.ioloop.IOLoop.instance())
    self.acs_url = acs_url
    self.cookies = None
    self.my_ip = None
    self.my_port = None
    self.ping_received = False
    self.state = self.CONNECT

  def state_update(self, sent_inform=None, on_hold=None,
                   cpe_to_acs_empty=None, acs_to_cpe_empty=None):
    if self.state == self.CONNECT:
      if sent_inform:
        self.state = self.ACTIVE
    elif self._active():
      if on_hold:
        self.state = self.ONHOLD
      elif cpe_to_acs_empty:
        self.state = self.NOMORE
    elif self._onhold():
      if on_hold is False:  # not just the default None; explicitly False
        self.state = self.ACTIVE
    elif self._nomore():
      if acs_to_cpe_empty:
        self.state = self.DONE

  def _connect(self):
    return self.state == self.CONNECT

  def _active(self):
    return self.state == self.ACTIVE

  def _onhold(self):
    return self.state == self.ONHOLD

  def _nomore(self):
    return self.state == self.NOMORE

  def _done(self):
    return self.state == self.DONE

  def inform_required(self):
    return True if self._connect() else False

  def request_allowed(self):
    return True if self._active() else False

  def response_allowed(self):
    return True if self._active() or self._onhold() or self._nomore() else False

  def should_close(self):
    return True if self._done() else False

  def __del__(self):
    self.close()

  def close(self):
    cache.flush()
    self.http = None
    return self.ping_received


class cache(object):
  """A global cache of arbitrary data for the lifetime of one CWMP session.

  @cwmp_session.cache is a decorator to cache the return
  value of a function for the remainder of the session with the ACS.
  Calling the function again with the same arguments will be serviced
  from the cache.

  This is intended for very expensive operations, particularly where
  a process is forked and its output parsed.
  """

  _thecache = dict()

  @staticmethod
  def flush():
    """Flush all cached data."""
    for k in cache._thecache.keys():
      del cache._thecache[k]

  def __init__(self, func):
    self.func = func
    self.obj = None

  def __get__(self, obj, objtype):
    """Support instance methods."""
    self.obj = obj
    return functools.partial(self.__call__, obj)

  def __call__(self, *args):
    key = self._cache_key(args)
    try:
      return cache._thecache[key]
    except KeyError:
      val = self.func(*args)
      cache._thecache[key] = val
      return val

  def _cache_key(self, *args):
    """Concatenate the function, object, and all arguments."""
    return '\0'.join([repr(x) for x in [self.func, self.obj, args]])


def main():
  # pylint: disable-msg=C6003
  print('# pipe this to grapviz, ex:')
  print('# ./cwmp_session.py | dot -Tpdf -ocwmp_session.pdf')
  print(graphviz)


if __name__ == '__main__':
  main()
