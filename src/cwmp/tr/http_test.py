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

"""Unit tests for http.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime
import mox
import os
import shutil
import sys
import tempfile
import time
import unittest
import xml.etree.ElementTree as ET

import google3
import dm_root
import tornado.httpclient
import tornado.ioloop
import tornado.testing
import tornado.util

import api
import cwmp_session
import cwmpdate
import download
import http


mock_http_client_stop = None
mock_http_clients = []
SOAPNS = '{http://schemas.xmlsoap.org/soap/envelope/}'
CWMPNS = '{urn:dslforum-org:cwmp-1-2}'


def GetMonotime():
  """Older tornado doesn't have monotime(); stay compatible."""
  if hasattr(tornado.util, 'monotime_impl'):
    return tornado.util.monotime_impl
  else:
    return time.time


def SetMonotime(func):
  """Older tornado doesn't have monotime(); stay compatible."""
  if hasattr(tornado.util, 'monotime_impl'):
    tornado.util.monotime_impl = func
  else:
    time.time = func


def StubOutMonotime(moxinstance):
  if hasattr(tornado.util, 'monotime_impl'):
    moxinstance.StubOutWithMock(tornado.util, 'monotime_impl')
  else:
    moxinstance.StubOutWithMock(time, 'time')


class MockHttpClient(object):
  def __init__(self, **kwargs):
    self.ResetMock()
    mock_http_clients.append(self)

  def ResetMock(self):
    self.req = None
    self.fetch_called = False

  def fetch(self, req, callback):
    print '%s: fetching: %s %s' % (self, req, callback)
    self.fetch_req = req
    self.fetch_callback = callback
    self.fetch_called = True
    mock_http_client_stop()


class MockPlatformConfig(object):
  def GetAcsUrl(self):
    return 'http://example.com/cwmp'

  def AcsAccessAttempt(self, url):
    pass

  def AcsAccessSuccess(self, url):
    pass


class HttpTest(tornado.testing.AsyncTestCase):
  def setUp(self):
    super(HttpTest, self).setUp()
    self.old_monotime = GetMonotime()
    self.advance_time = 0
    self.old_HTTPCLIENT = cwmp_session.HTTPCLIENT
    cwmp_session.HTTPCLIENT = MockHttpClient
    global mock_http_client_stop
    mock_http_client_stop = self.stop
    self.removedirs = list()
    self.removefiles = list()
    del mock_http_clients[:]

  def tearDown(self):
    super(HttpTest, self).tearDown()
    SetMonotime(self.old_monotime)
    cwmp_session.HTTPCLIENT = self.old_HTTPCLIENT
    for d in self.removedirs:
      shutil.rmtree(d)
    for f in self.removefiles:
      os.remove(f)
    del mock_http_clients[:]

  def advanceTime(self):
    return 420000.0 + self.advance_time

  def getCpe(self):
    dm_root.PLATFORMDIR = '../platform'
    root = dm_root.DeviceModelRoot(self.io_loop, 'fakecpe')
    cpe = api.CPE(root)
    dldir = tempfile.mkdtemp()
    self.removedirs.append(dldir)
    cfdir = tempfile.mkdtemp()
    self.removedirs.append(cfdir)
    cpe.download_manager.SetDirectories(config_dir=cfdir, download_dir=dldir)
    cpe_machine = http.Listen(ip=None, port=0,
                              ping_path='/ping/http_test',
                              acs=None, cpe=cpe, cpe_listener=False,
                              platform_config=MockPlatformConfig(),
                              ioloop=self.io_loop)
    return cpe_machine

  def testMaxEnvelopes(self):
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.wait()

    self.assertEqual(len(mock_http_clients), 1)
    ht = mock_http_clients[0]
    self.assertTrue(ht.fetch_called)

    root = ET.fromstring(ht.fetch_req.body)
    envelope = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/MaxEnvelopes')
    self.assertTrue(envelope is not None)
    self.assertEqual(envelope.text, '1')

  def testCurrentTime(self):
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.wait()

    self.assertEqual(len(mock_http_clients), 1)
    ht = mock_http_clients[0]
    self.assertTrue(ht.fetch_called)

    root = ET.fromstring(ht.fetch_req.body)
    ctime = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/CurrentTime')
    self.assertTrue(ctime is not None)
    self.assertTrue(cwmpdate.valid(ctime.text))

  def testLookupDevIP6(self):
    http.PROC_IF_INET6 = 'testdata/http/if_inet6'
    cpe_machine = self.getCpe()
    self.assertEqual(cpe_machine.LookupDevIP6('eth0'),
                     '11:2233:4455:6677:8899:aabb:ccdd:eeff')
    self.assertEqual(cpe_machine.LookupDevIP6('foo0'), 0)

  def testRetryCount(self):
    SetMonotime(self.advanceTime)
    cpe_machine = self.getCpe()
    cpe_machine.Startup()
    self.wait(timeout=20)

    self.assertEqual(len(mock_http_clients), 1)
    ht = mock_http_clients[0]
    self.assertTrue(ht.fetch_called)

    root = ET.fromstring(ht.fetch_req.body)
    retry = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/RetryCount')
    self.assertTrue(retry is not None)
    self.assertEqual(retry.text, '0')

    # Fail the first request
    httpresp = tornado.httpclient.HTTPResponse(ht.fetch_req, 404)
    ht.fetch_callback(httpresp)

    self.advance_time += 10
    self.wait(timeout=20)
    self.assertEqual(len(mock_http_clients), 2)
    ht = mock_http_clients[1]

    root = ET.fromstring(ht.fetch_req.body)
    retry = root.find(SOAPNS + 'Body/' + CWMPNS + 'Inform/RetryCount')
    self.assertTrue(retry is not None)
    self.assertEqual(retry.text, '1')

  def testNewPingSession(self):
    cpe_machine = self.getCpe()
    cpe_machine.previous_ping_time = 0

    # Create mocks of ioloop, and stubout the time function.
    m = mox.Mox()
    ioloop_mock = m.CreateMock(tornado.ioloop.IOLoop)
    m.StubOutWithMock(cpe_machine, "_NewSession")
    StubOutMonotime(m)

    # First call to _NewSession should get the time and trigger a new session
    GetMonotime()().AndReturn(1000)
    cpe_machine._NewSession(mox.IsA(str))

    # Second call to _NewSession should queue a session
    GetMonotime()().AndReturn(1001)
    ioloop_mock.add_timeout(mox.IsA(datetime.timedelta),
                            mox.IgnoreArg()).AndReturn(1)

    # Third call should get the time and then not do anything
    # since a session is queued.
    GetMonotime()().AndReturn(1001)

    # And the call to _NewTimeoutSession should call through to
    # NewPingSession, and start a new session
    GetMonotime()().AndReturn(1000 + cpe_machine.rate_limit_seconds)
    ioloop_mock.add_timeout(mox.IsA(datetime.timedelta),
                            mox.IgnoreArg()).AndReturn(2)
    cpe_machine.ioloop = ioloop_mock
    m.ReplayAll()

    # Real test starts here.
    cpe_machine._NewPingSession()
    cpe_machine._NewPingSession()
    cpe_machine._NewPingSession()
    cpe_machine._NewTimeoutPingSession()

    # Verify everything was called correctly.
    m.VerifyAll()

  def testNewPeriodicSession(self):
    """Tests that _NewSession is called if the event queue is empty."""
    cpe_machine = self.getCpe()

    # Create mocks of ioloop, and stubout the time function.
    m = mox.Mox()
    m.StubOutWithMock(cpe_machine, '_NewSession')
    cpe_machine._NewSession('2 PERIODIC')
    m.ReplayAll()

    cpe_machine.NewPeriodicSession()
    m.VerifyAll()

  def testNewPeriodicSessionPending(self):
    """Tests that no new periodic session starts if there is one pending."""
    cpe_machine = self.getCpe()

    # Create mocks of ioloop, and stubout the time function.
    m = mox.Mox()
    m.StubOutWithMock(cpe_machine, 'Run')
    cpe_machine.Run()
    m.ReplayAll()

    self.assertFalse(('2 PERIODIC', None) in cpe_machine.event_queue)
    cpe_machine.NewPeriodicSession()
    self.assertTrue(('2 PERIODIC', None) in cpe_machine.event_queue)
    cpe_machine.NewPeriodicSession()
    m.ReplayAll()

  def testEventQueue(self):
    cpe_machine = self.getCpe()
    m = mox.Mox()
    m.StubOutWithMock(sys, 'exit')
    sys.exit(1)
    sys.exit(1)
    sys.exit(1)
    sys.exit(1)
    m.ReplayAll()

    for i in range(64):
      cpe_machine.event_queue.append(i)

    cpe_machine.event_queue.append(100)
    cpe_machine.event_queue.appendleft(200)
    cpe_machine.event_queue.extend([300])
    cpe_machine.event_queue.extendleft([400])

    cpe_machine.event_queue.clear()
    cpe_machine.event_queue.append(10)
    cpe_machine.event_queue.clear()
    m.VerifyAll()


class TestManagementServer(object):
  ConnectionRequestUsername = 'username'
  ConnectionRequestPassword = 'password'


class PingTest(tornado.testing.AsyncHTTPTestCase):
  def ping_callback(self):
    self.ping_calledback = True

  def get_app(self):
    return tornado.web.Application(
        [('/', http.PingHandler, dict(cpe_ms=TestManagementServer(),
                                      callback=self.ping_callback))])

  def test_ping(self):
    self.ping_calledback = False
    self.http_client.fetch(self.get_url('/'), self.stop)
    response = self.wait()
    self.assertEqual(response.error.code, 401)
    self.assertFalse(self.ping_calledback)
    self.assertTrue(response.body.find('qop'))


class TestManagementServer(object):
  ConnectionRequestUsername = 'username'
  ConnectionRequestPassword = 'password'


class PingTest(tornado.testing.AsyncHTTPTestCase):
  def ping_callback(self):
    self.ping_calledback = True

  def get_app(self):
    return tornado.web.Application(
        [('/', http.PingHandler, dict(cpe_ms=TestManagementServer(),
                                      callback=self.ping_callback))])

  def test_ping(self):
    self.ping_calledback = False
    self.http_client.fetch(self.get_url('/'), self.stop)
    response = self.wait()
    self.assertEqual(response.error.code, 401)
    self.assertFalse(self.ping_calledback)
    self.assertTrue(response.body.find('qop'))


if __name__ == '__main__':
  unittest.main()
