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

"""Unit tests for ManagementServer implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import copy
import unittest

import google3
import management_server


class MockConfig(object):
  def __init__(self):
    pass


class MockCpeManagementServer(object):
  def __init__(self):
    self.CWMPRetryIntervalMultiplier = 1
    self.CWMPRetryMinimumWaitInterval = 2
    self.ConnectionRequestPassword = 'ConnectPassword'
    self.ConnectionRequestUsername = 'ConnectUsername'
    self.ConnectionRequestURL = 'http://example.com/'
    self.DefaultActiveNotificationThrottle = 3
    self.EnableCWMP = True
    self.ParameterKey = 'ParameterKey'
    self.Password = 'Password'
    self.PeriodicInformEnable = False
    self.PeriodicInformInterval = 4
    self.PeriodicInformTime = 5
    self.URL = 'http://example.com/'
    self.Username = 'Username'

  def StartTransaction(self):
    self.copy = copy.copy(self)

  def CommitTransaction(self):
    del self.copy

  def AbandonTransaction(self):
    for k,v in self.copy.__dict__.iteritems():
      self.__dict__[k] = v
    del self.copy


class ManagementServerTest(unittest.TestCase):
  """Tests for management_server.py."""

  def testGetMgmt181(self):
    mgmt = MockCpeManagementServer()
    mgmt181 = management_server.ManagementServer181(mgmt)
    self.assertEqual(mgmt181.ParameterKey, mgmt.ParameterKey)
    self.assertEqual(mgmt181.EnableCWMP, mgmt.EnableCWMP)
    self.assertTrue(mgmt181.UpgradesManaged)

  def testGetMgmt98(self):
    mgmt = MockCpeManagementServer()
    mgmt98 = management_server.ManagementServer98(mgmt)
    self.assertEqual(mgmt98.ParameterKey, mgmt.ParameterKey)
    self.assertEqual(mgmt98.EnableCWMP, mgmt.EnableCWMP)
    self.assertTrue(mgmt98.UpgradesManaged)
    mgmt98.ValidateExports()

  def testSetMgmt181(self):
    mgmt = MockCpeManagementServer()
    mgmt181 = management_server.ManagementServer181(mgmt)
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 1)
    self.assertEqual(mgmt181.CWMPRetryIntervalMultiplier, 1)
    mgmt181.CWMPRetryIntervalMultiplier = 2
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 2)
    self.assertEqual(mgmt181.CWMPRetryIntervalMultiplier, 2)
    mgmt181.ValidateExports()

  def testSetMgmt98(self):
    mgmt = MockCpeManagementServer()
    mgmt98 = management_server.ManagementServer98(mgmt)
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 1)
    self.assertEqual(mgmt98.CWMPRetryIntervalMultiplier, 1)
    mgmt98.CWMPRetryIntervalMultiplier = 2
    self.assertEqual(mgmt.CWMPRetryIntervalMultiplier, 2)
    self.assertEqual(mgmt98.CWMPRetryIntervalMultiplier, 2)

  def testDelMgmt181(self):
    mgmt = MockCpeManagementServer()
    mgmt181 = management_server.ManagementServer181(mgmt)
    delattr(mgmt181, 'CWMPRetryIntervalMultiplier')
    self.assertFalse(hasattr(mgmt, 'CWMPRetryIntervalMultiplier'))

  def testDelMgmt98(self):
    mgmt = MockCpeManagementServer()
    mgmt98 = management_server.ManagementServer98(mgmt)
    delattr(mgmt98, 'CWMPRetryIntervalMultiplier')
    self.assertFalse(hasattr(mgmt, 'CWMPRetryIntervalMultiplier'))

  def TransactionTester(self, mgmt_server):
    mgmt_server.StartTransaction()
    mgmt_server.CommitTransaction()

    mgmt_server.StartTransaction()
    mgmt_server.AbandonTransaction()

    save_pass = mgmt_server.ConnectionRequestPassword
    save_user = mgmt_server.ConnectionRequestUsername
    mgmt_server.StartTransaction()
    mgmt_server.ConnectionRequestUsername = 'username'
    mgmt_server.ConnectionRequestPassword = 'pass'
    mgmt_server.AbandonTransaction()
    self.assertEqual(save_pass, mgmt_server.ConnectionRequestPassword)
    self.assertEqual(save_user, mgmt_server.ConnectionRequestUsername)

    mgmt_server.StartTransaction()
    mgmt_server.ConnectionRequestUsername = 'newname'
    mgmt_server.ConnectionRequestPassword = 'newpass'
    mgmt_server.CommitTransaction()
    self.assertEqual('newpass', mgmt_server.ConnectionRequestPassword)
    self.assertEqual('newname', mgmt_server.ConnectionRequestUsername)

  def testTransactions181(self):
    mgmt = MockCpeManagementServer()
    mgmt181 = management_server.ManagementServer181(mgmt)
    self.TransactionTester(mgmt181)

  def testTransactions98(self):
    mgmt = MockCpeManagementServer()
    mgmt98 = management_server.ManagementServer98(mgmt)
    self.TransactionTester(mgmt98)

if __name__ == '__main__':
  unittest.main()
