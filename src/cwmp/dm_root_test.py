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

"""Unit tests for dm_root.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest
import google3
import dm_root
import tr.tr098_v1_4
import tr.tr181_v2_2


BASE181 = tr.tr181_v2_2.Device_v2_2.Device
BASE98 = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice


class MockTr181(BASE181):
  pass


class MockTr98(BASE98):
  pass


class MockManagement(object):
  def __init__(self):
    self.EnableCWMP = False


class DeviceModelRootTest(unittest.TestCase):
  def testAddManagementServer(self):
    root = dm_root.DeviceModelRoot(loop=None, platform=None)
    mgmt = MockManagement()
    root.add_management_server(mgmt)  # should do nothing.

    root.Device = MockTr181()
    root.InternetGatewayDevice = MockTr98()
    root.Export(objects=['Device', 'InternetGatewayDevice'])
    self.assertFalse(isinstance(root.InternetGatewayDevice.ManagementServer,
                                BASE98.ManagementServer))
    self.assertFalse(isinstance(root.Device.ManagementServer,
                                BASE181.ManagementServer))
    root.add_management_server(mgmt)  # should do nothing.
    self.assertTrue(isinstance(root.InternetGatewayDevice.ManagementServer,
                               BASE98.ManagementServer))
    self.assertTrue(isinstance(root.Device.ManagementServer,
                               BASE181.ManagementServer))


if __name__ == '__main__':
  unittest.main()
