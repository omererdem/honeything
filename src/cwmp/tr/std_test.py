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
#
"""Tests for auto-generated tr???_*.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import unittest
import core
import tr098_v1_2 as tr098


class MyModel(tr098.InternetGatewayDevice_v1_4):
  def __init__(self):
    tr098.InternetGatewayDevice_v1_4.__init__(self)
    self.InternetGatewayDevice = core.TODO()
    u = self.UDPEchoConfig = self.UDPEchoConfig()
    u.BytesReceived = 0
    u.Enable = True
    u.PacketsReceived = 0
    u.TimeFirstPacketReceived = 0
    u.EchoPlusEnabled = False
    u.UDPPort = 0
    u.EchoPlusSupported = False
    u.Interface = ''
    u.PacketsResponded = ''
    u.SourceIPAddress = '1.2.3.4'
    u.TimeLastPacketReceived = 0
    u.BytesResponded = 0
    self.UploadDiagnostics = core.TODO()
    self.Capabilities = core.TODO()
    self.DownloadDiagnostics = core.TODO()


class StdTest(unittest.TestCase):
  def testStd(self):
    o = MyModel()
    o.ValidateExports()
    print core.Dump(o)


if __name__ == '__main__':
  unittest.main()
