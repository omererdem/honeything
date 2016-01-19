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

"""Unit tests for tr-181 Ethernet.* implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest
import google3
import tr.tr181_v2_2 as tr181
import ethernet
import netdev


BASEETHERNET = tr181.Device_v2_2.Device.Ethernet


class EthernetTest(unittest.TestCase):
  """Tests for ethernet.py."""

  def setUp(self):
    self.old_PROC_NET_DEV = netdev.PROC_NET_DEV
    self.old_PYNETIFCONF = ethernet.PYNETIFCONF

  def tearDown(self):
    netdev.PROC_NET_DEV = self.old_PROC_NET_DEV
    ethernet.PYNETIFCONF = self.old_PYNETIFCONF

  def testInterfaceStatsGood(self):
    netdev.PROC_NET_DEV = 'testdata/ethernet/net_dev'
    eth = ethernet.EthernetInterfaceStatsLinux26('foo0')
    eth.ValidateExports()

    self.assertEqual(eth.BroadcastPacketsReceived, None)
    self.assertEqual(eth.BroadcastPacketsSent, None)
    self.assertEqual(eth.BytesReceived, '1')
    self.assertEqual(eth.BytesSent, '9')
    self.assertEqual(eth.DiscardPacketsReceived, '4')
    self.assertEqual(eth.DiscardPacketsSent, '11')
    self.assertEqual(eth.ErrorsReceived, '9')
    self.assertEqual(eth.ErrorsSent, '12')
    self.assertEqual(eth.MulticastPacketsReceived, '8')
    self.assertEqual(eth.MulticastPacketsSent, None)
    self.assertEqual(eth.PacketsReceived, '100')
    self.assertEqual(eth.PacketsSent, '10')
    self.assertEqual(eth.UnicastPacketsReceived, '92')
    self.assertEqual(eth.UnicastPacketsSent, '10')
    self.assertEqual(eth.UnknownProtoPacketsReceived, None)

  def testInterfaceStatsNonexistent(self):
    netdev.PROC_NET_DEV = 'testdata/ethernet/net_dev'
    eth = ethernet.EthernetInterfaceStatsLinux26('doesnotexist0')
    exception_raised = False
    try:
      eth.ErrorsReceived
    except AttributeError:
      exception_raised = True
    self.assertTrue(exception_raised)

  def _CheckEthernetInterfaceParameters(self, ifname, upstream, eth, pynet):
    self.assertEqual(eth.DuplexMode, 'Auto')
    self.assertEqual(eth.Enable, True)
    self.assertEqual(eth.LastChange, '0001-01-01T00:00:00Z')
    self.assertFalse(eth.LowerLayers)
    self.assertEqual(eth.MACAddress, pynet.v_mac)
    self.assertEqual(eth.MaxBitRate, -1)
    self.assertEqual(eth.Name, ifname)
    self.assertEqual(eth.Upstream, upstream)
    self.assertEqual(eth.X_CATAWAMPUS_ORG_ActualBitRate, pynet.v_speed)
    self.assertEqual(eth.X_CATAWAMPUS_ORG_ActualDuplexMode,
                     'Full' if pynet.v_duplex else 'Half')

  def testValidateExports(self):
    ethernet.PYNETIFCONF = MockPynet
    netdev.PROC_NET_DEV = 'testdata/ethernet/net_dev'
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    eth.ValidateExports()

  def testInterfaceGood(self):
    ethernet.PYNETIFCONF = MockPynet
    netdev.PROC_NET_DEV = 'testdata/ethernet/net_dev'
    upstream = False

    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)

    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)

    MockPynet.v_is_up = False
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)

    MockPynet.v_duplex = False
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)

    MockPynet.v_auto = False
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)

    MockPynet.v_link_up = False
    eth = ethernet.EthernetInterfaceLinux26('foo0')
    self._CheckEthernetInterfaceParameters('foo0', upstream, eth, MockPynet)


class MockPynet(object):
  v_is_up = True
  v_mac = '00:11:22:33:44:55'
  v_speed = 1000
  v_duplex = True
  v_auto = True
  v_link_up = True

  def __init__(self, ifname):
    self.ifname = ifname

  def is_up(self):
    return self.v_is_up

  def get_mac(self):
    return self.v_mac

  def get_link_info(self):
    return (self.v_speed, self.v_duplex, self.v_auto, self.v_link_up)


if __name__ == '__main__':
  unittest.main()
