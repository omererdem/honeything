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

"""Unit tests for cpe_management_server.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import copy
import datetime
import unittest

import google3
import cpe_management_server as ms
import cwmpdate


periodic_callbacks = []


class MockIoloop(object):
  def __init__(self):
    self.timeout_time = None
    self.timeout_callback = None
    self.remove_handle = None
    self.handle = 1

  def add_timeout(self, time, callback, monotonic=None):
    self.timeout_time = time
    self.timeout_callback = callback
    return self.handle

  def remove_timeout(self, timeout):
    self.remove_handle = timeout


class MockPeriodicCallback(object):
  def __init__(self, callback, callback_time, io_loop=None):
    self.callback = callback
    self.callback_time = callback_time
    self.io_loop = io_loop
    self.start_called = False
    self.stop_called = False
    periodic_callbacks.append(self)

  def start(self):
    self.start_called = True

  def stop(self):
    self.stop_called = True
    periodic_callbacks.remove(self)


class MockPlatformConfig(object):
  def __init__(self):
    self.set_acs_raise = True
    self.set_acs_url_called = False
    self.acs_url = 'http://acs.example.com/cwmp'

  def SetAcsUrl(self, url):
    self.set_acs_url_called = True
    if self.set_acs_raise:
      raise AttributeError('read-only param')
    else:
      self.acs_url = url

  def GetAcsUrl(self):
    return self.acs_url


class FakePlatformConfig(object):
  def GetAcsUrl(self):
    return None


class CpeManagementServerTest(unittest.TestCase):
  """tests for http.py CpeManagementServer."""

  def setUp(self):
    self.start_session_called = False
    del periodic_callbacks[:]

  def testIsIp6Address(self):
    cpe_ms = ms.CpeManagementServer(platform_config=FakePlatformConfig(), port=5,
                                    ping_path='/ping/path')
    self.assertTrue(cpe_ms._isIp6Address('fe80::21d:9ff:fe11:f55f'))
    self.assertTrue(cpe_ms._isIp6Address('2620:0:1000:5200:222:3ff:fe44:5555'))
    self.assertFalse(cpe_ms._isIp6Address('1.2.3.4'))
    self.assertFalse(cpe_ms._isIp6Address('foobar'))

  def testConnectionRequestURL(self):
    cpe_ms = ms.CpeManagementServer(platform_config=FakePlatformConfig(), port=5,
                                    ping_path='/ping/path')
    cpe_ms.my_ip = '1.2.3.4'
    self.assertEqual(cpe_ms.ConnectionRequestURL, 'http://1.2.3.4:5/ping/path')
    cpe_ms.my_ip = '2620:0:1000:5200:222:3ff:fe44:5555'
    self.assertEqual(cpe_ms.ConnectionRequestURL,
                     'http://[2620:0:1000:5200:222:3ff:fe44:5555]:5/ping/path')

  def testAcsUrl(self):
    pc = MockPlatformConfig()
    cpe_ms = ms.CpeManagementServer(platform_config=pc, port=0, ping_path='')
    self.assertEqual(cpe_ms.URL, 'http://acs.example.com/cwmp')
    self.assertRaises(AttributeError, cpe_ms.SetURL, 'http://example.com/')
    self.assertTrue(pc.set_acs_url_called)
    pc.set_acs_raise = False
    pc.set_acs_url_called = False
    cpe_ms.URL = 'http://example.com/'
    self.assertTrue(pc.set_acs_url_called)
    self.assertEqual(pc.acs_url, 'http://example.com/')

  def GetParameterKey(self):
    return 'ParameterKey'

  def testParameterKey(self):
    cpe_ms = ms.CpeManagementServer(platform_config=FakePlatformConfig(), port=0, ping_path='/',
                                    get_parameter_key=self.GetParameterKey)
    self.assertEqual(cpe_ms.ParameterKey, self.GetParameterKey())

  def start_session(self):
    self.start_session_called = True

  def testPeriodicEnable(self):
    ms.PERIODIC_CALLBACK = MockPeriodicCallback
    io = MockIoloop()
    cpe_ms = ms.CpeManagementServer(platform_config=FakePlatformConfig(), port=0, ping_path='/',
                                    start_periodic_session=self.start_session,
                                    ioloop=io)
    cpe_ms.PeriodicInformEnable = 'true'
    cpe_ms.PeriodicInformInterval = '15'
    # cpe_ms should schedule the callbacks when Enable and Interval both set

    self.assertEqual(io.timeout_time, datetime.timedelta(0.0))
    self.assertEqual(len(periodic_callbacks), 1)
    cb = periodic_callbacks[0]
    self.assertTrue(cb.callback)
    self.assertEqual(cb.callback_time, 15 * 1000)
    self.assertEqual(cb.io_loop, io)

    io.timeout_callback()
    self.assertTrue(cb.start_called)

  def testPeriodicLongInterval(self):
    ms.PERIODIC_CALLBACK = MockPeriodicCallback
    io = MockIoloop()
    cpe_ms = ms.CpeManagementServer(platform_config=FakePlatformConfig(), port=0, ping_path='/',
                                    start_periodic_session=self.start_session,
                                    ioloop=io)
    cpe_ms.PeriodicInformEnable = 'true'
    cpe_ms.PeriodicInformTime = cwmpdate.format(datetime.datetime.now())
    cpe_ms.PeriodicInformInterval = '1200'

    # Just check that the delay is reasonable
    self.assertNotEqual(io.timeout_time, datetime.timedelta(seconds=0))

  def assertWithinRange(self, c, minr, maxr):
    self.assertTrue(minr <= c <= maxr)

  def testSessionRetryWait(self):
    """Test $SPEC3 Table3 timings."""

    cpe_ms = ms.CpeManagementServer(platform_config=FakePlatformConfig(), port=5, ping_path='/')
    cpe_ms.PeriodicInformInterval = 100000
    for _ in range(1000):
      self.assertEqual(cpe_ms.SessionRetryWait(0), 0)
      self.assertTrue(5 <= cpe_ms.SessionRetryWait(1) <= 10)
      self.assertTrue(10 <= cpe_ms.SessionRetryWait(2) <= 20)
      self.assertTrue(20 <= cpe_ms.SessionRetryWait(3) <= 40)
      self.assertTrue(40 <= cpe_ms.SessionRetryWait(4) <= 80)
      self.assertTrue(80 <= cpe_ms.SessionRetryWait(5) <= 160)
      self.assertTrue(160 <= cpe_ms.SessionRetryWait(6) <= 320)
      self.assertTrue(320 <= cpe_ms.SessionRetryWait(7) <= 640)
      self.assertTrue(640 <= cpe_ms.SessionRetryWait(8) <= 1280)
      self.assertTrue(1280 <= cpe_ms.SessionRetryWait(9) <= 2560)
      self.assertTrue(2560 <= cpe_ms.SessionRetryWait(10) <= 5120)
      self.assertTrue(2560 <= cpe_ms.SessionRetryWait(99) <= 5120)
    cpe_ms.CWMPRetryMinimumWaitInterval = 10
    cpe_ms.CWMPRetryIntervalMultiplier = 2500
    for _ in range(1000):
      self.assertEqual(cpe_ms.SessionRetryWait(0), 0)
      self.assertTrue(10 <= cpe_ms.SessionRetryWait(1) <= 25)
      self.assertTrue(25 <= cpe_ms.SessionRetryWait(2) <= 62)
      self.assertTrue(62 <= cpe_ms.SessionRetryWait(3) <= 156)
      self.assertTrue(156 <= cpe_ms.SessionRetryWait(4) <= 390)
      self.assertTrue(390 <= cpe_ms.SessionRetryWait(5) <= 976)
      self.assertTrue(976 <= cpe_ms.SessionRetryWait(6) <= 2441)
      self.assertTrue(2441 <= cpe_ms.SessionRetryWait(7) <= 6103)
      self.assertTrue(6103 <= cpe_ms.SessionRetryWait(8) <= 15258)
      self.assertTrue(15258 <= cpe_ms.SessionRetryWait(9) <= 38146)
      self.assertTrue(38146 <= cpe_ms.SessionRetryWait(10) <= 95367)
      self.assertTrue(38146 <= cpe_ms.SessionRetryWait(99) <= 95367)
    # Check that the time never exceeds the periodic inform time.
    cpe_ms.PeriodicInformInterval = 30
    for _ in range(1000):
      self.assertEqual(cpe_ms.SessionRetryWait(0), 0)
      self.assertTrue(10 <= cpe_ms.SessionRetryWait(1) <= 25)
      self.assertTrue(12 <= cpe_ms.SessionRetryWait(2) <= 30)
      self.assertTrue(12 <= cpe_ms.SessionRetryWait(3) <= 30)

  def testValidateServer(self):
    def TryUrl(cpe, value):
      valid = True
      try:
        cpe_ms.ValidateAcsUrl(value)
      except ValueError:
        valid = False
      return valid

    cpe_ms = ms.CpeManagementServer(
        platform_config=FakePlatformConfig(), port=5, ping_path='/',
        restrict_acs_hosts='google.com .gfsvc.com foo.com')
    self.assertTrue(TryUrl(cpe_ms, 'https://bugger.gfsvc.com'))
    self.assertTrue(TryUrl(cpe_ms, 'https://acs.prod.gfsvc.com'))
    self.assertTrue(TryUrl(cpe_ms, 'https://acs.prod.google.com'))
    self.assertTrue(TryUrl(cpe_ms, 'https://google.com'))
    self.assertFalse(TryUrl(cpe_ms, 'https://imposter.evilgfsvc.com'))
    self.assertFalse(TryUrl(cpe_ms, 'https://evilgfsvc.com'))
    self.assertFalse(TryUrl(cpe_ms, 'https://gfsvc.com.evil.com'))

    # No restrictions
    cpe_ms = ms.CpeManagementServer(
        platform_config=FakePlatformConfig(), port=5, ping_path='/')
    self.assertTrue(TryUrl(cpe_ms, 'https://bugger.gfsvc.com'))
    self.assertTrue(TryUrl(cpe_ms, 'https://gfsvc.com.evil.com'))

    # Single domain
    cpe_ms = ms.CpeManagementServer(
        platform_config=FakePlatformConfig(), port=5, ping_path='/',
        restrict_acs_hosts='.gfsvc.com')
    self.assertTrue(TryUrl(cpe_ms, 'https://bugger.gfsvc.com'))
    self.assertTrue(TryUrl(cpe_ms, 'https://acs.prod.gfsvc.com'))
    self.assertFalse(TryUrl(cpe_ms, 'https://acs.prod.google.com'))
    self.assertFalse(TryUrl(cpe_ms, 'https://google.com'))
    self.assertFalse(TryUrl(cpe_ms, 'https://imposter.evilgfsvc.com'))
    self.assertFalse(TryUrl(cpe_ms, 'https://evilgfsvc.com'))
    self.assertFalse(TryUrl(cpe_ms, 'https://gfsvc.com.evil.com'))

  def testReadParameters(self):
    cpe_ms = ms.CpeManagementServer(
        platform_config=None, port=5, ping_path='/',
        restrict_acs_hosts='.gfsvc.com')
    _ = cpe_ms.CWMPRetryMinimumWaitInterval
    _ = cpe_ms.CWMPRetryIntervalMultiplier
    _ = cpe_ms.ConnectionRequestPassword
    _ = cpe_ms.ConnectionRequestUsername
    _ = cpe_ms.DefaultActiveNotificationThrottle
    _ = cpe_ms.EnableCWMP
    _ = cpe_ms.PeriodicInformEnable
    _ = cpe_ms.PeriodicInformInterval
    _ = cpe_ms.PeriodicInformTime
    _ = cpe_ms.Password
    _ = cpe_ms.Username

  def testWriteParameters(self):
    cpe_ms = ms.CpeManagementServer(
        platform_config=None, port=5, ping_path='/',
        restrict_acs_hosts='.gfsvc.com')
    cpe_ms.CWMPRetryMinimumWaitInterval = 10
    cpe_ms.CWMPRetryIntervalMultiplier = 100
    cpe_ms.ConnectionRequestPassword = 'pass'
    cpe_ms.ConnectionRequestUsername = 'user'
    cpe_ms.DefaultActiveNotificationThrottle = True
    cpe_ms.PeriodicInformEnable = True
    cpe_ms.PeriodicInformInterval = 10
    cpe_ms.PeriodicInformTime = '2012-08-22T15:50:14.725772Z'
    cpe_ms.Password = ' pass'
    cpe_ms.Username = ' user'

  def testTransaction(self):
    cpe_ms = ms.CpeManagementServer(
        platform_config=None, port=5, ping_path='/',
        restrict_acs_hosts='.gfsvc.com')
    orig = copy.deepcopy(cpe_ms.config)
    # sanity
    self.assertEqual(orig.CWMPRetryMinimumWaitInterval,
                     cpe_ms.CWMPRetryMinimumWaitInterval)
    cpe_ms.StartTransaction()
    cpe_ms.AbandonTransaction()
    self.assertEqual(orig.CWMPRetryMinimumWaitInterval,
                     cpe_ms.CWMPRetryMinimumWaitInterval)

    cpe_ms.StartTransaction()
    cpe_ms.CommitTransaction()
    self.assertEqual(orig.CWMPRetryMinimumWaitInterval,
                     cpe_ms.CWMPRetryMinimumWaitInterval)

    cpe_ms.StartTransaction()
    cpe_ms.CWMPRetryMinimumWaitInterval *= 2
    cpe_ms.AbandonTransaction()
    self.assertEqual(orig.CWMPRetryMinimumWaitInterval,
                     cpe_ms.CWMPRetryMinimumWaitInterval)

    cpe_ms.StartTransaction()
    cpe_ms.CWMPRetryMinimumWaitInterval *= 2
    cpe_ms.CommitTransaction()
    self.assertEqual(orig.CWMPRetryMinimumWaitInterval * 2,
                     cpe_ms.CWMPRetryMinimumWaitInterval)

if __name__ == '__main__':
  unittest.main()
