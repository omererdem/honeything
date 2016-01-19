#!/usr/bin/python
# Copyright 2012 Google Inc. All Rights Reserved.
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

"""Unit tests for tr-181 Device.MoCA.* implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest
import google3
import brcmmoca
import netdev


class MocaTest(unittest.TestCase):
  """Tests for brcmmoca.py."""

  def setUp(self):
    self.old_MOCACTL = brcmmoca.MOCACTL
    self.old_PYNETIFCONF = brcmmoca.PYNETIFCONF
    self.old_PROC_NET_DEV = netdev.PROC_NET_DEV

  def tearDown(self):
    brcmmoca.MOCACTL = self.old_MOCACTL
    brcmmoca.PYNETIFCONF = self.old_PYNETIFCONF
    netdev.PROC_NET_DEV = self.old_PROC_NET_DEV

  def testMocaInterfaceStatsGood(self):
    netdev.PROC_NET_DEV = 'testdata/brcmmoca/proc/net/dev'
    moca = brcmmoca.BrcmMocaInterfaceStatsLinux26('foo0')
    moca.ValidateExports()

    self.assertEqual(moca.BroadcastPacketsReceived, None)
    self.assertEqual(moca.BroadcastPacketsSent, None)
    self.assertEqual(moca.BytesReceived, '1')
    self.assertEqual(moca.BytesSent, '9')
    self.assertEqual(moca.DiscardPacketsReceived, '4')
    self.assertEqual(moca.DiscardPacketsSent, '11')
    self.assertEqual(moca.ErrorsReceived, '9')
    self.assertEqual(moca.ErrorsSent, '12')
    self.assertEqual(moca.MulticastPacketsReceived, '8')
    self.assertEqual(moca.MulticastPacketsSent, None)
    self.assertEqual(moca.PacketsReceived, '100')
    self.assertEqual(moca.PacketsSent, '10')
    self.assertEqual(moca.UnicastPacketsReceived, '92')
    self.assertEqual(moca.UnicastPacketsSent, '10')
    self.assertEqual(moca.UnknownProtoPacketsReceived, None)

  def testMocaInterfaceStatsNonexistent(self):
    netdev.PROC_NET_DEV = 'testdata/brcmmoca/proc/net/dev'
    moca = brcmmoca.BrcmMocaInterfaceStatsLinux26('doesnotexist0')
    exception_raised = False
    try:
      moca.ErrorsReceived
    except AttributeError:
      exception_raised = True
    self.assertTrue(exception_raised)

  def testMocaInterface(self):
    brcmmoca.PYNETIFCONF = MockPynet
    brcmmoca.MOCACTL = 'testdata/brcmmoca/mocactl'
    netdev.PROC_NET_DEV = 'testdata/brcmmoca/proc/net/dev'
    moca = brcmmoca.BrcmMocaInterface(ifname='foo0', upstream=False)
    moca.ValidateExports()
    self.assertEqual(moca.Name, 'foo0')
    self.assertEqual(moca.LowerLayers, '')
    self.assertFalse(moca.Upstream)
    self.assertEqual(moca.MACAddress, MockPynet.v_mac)
    moca = brcmmoca.BrcmMocaInterface(ifname='foo0', upstream=True)
    self.assertTrue(moca.Upstream)
    MockPynet.v_is_up = True
    MockPynet.v_link_up = True
    self.assertEqual(moca.Status, 'Up')
    MockPynet.v_link_up = False
    self.assertEqual(moca.Status, 'Dormant')
    MockPynet.v_is_up = False
    self.assertEqual(moca.Status, 'Down')
    self.assertEqual(moca.FirmwareVersion, '5.6.789')
    self.assertEqual(moca.HighestVersion, '1.1')
    self.assertEqual(moca.CurrentVersion, '1.1')
    self.assertEqual(moca.BackupNC, '5')
    self.assertFalse(moca.PrivacyEnabled)
    self.assertEqual(moca.CurrentOperFreq, 999)
    self.assertEqual(moca.LastOperFreq, 899)
    self.assertEqual(moca.NetworkCoordinator, 1)
    self.assertEqual(moca.NodeID, 2)
    self.assertTrue(moca.QAM256Capable)
    self.assertEqual(moca.PacketAggregationCapability, 10)

  def testMocaInterfaceAlt(self):
    brcmmoca.PYNETIFCONF = MockPynet
    brcmmoca.MOCACTL = 'testdata/brcmmoca/mocactl_alt'
    moca = brcmmoca.BrcmMocaInterface(ifname='foo0', upstream=False)
    self.assertEqual(moca.HighestVersion, '1.0')
    self.assertEqual(moca.CurrentVersion, '2.0')
    self.assertEqual(moca.BackupNC, '2')
    self.assertTrue(moca.PrivacyEnabled)
    self.assertFalse(moca.QAM256Capable)
    self.assertEqual(moca.PacketAggregationCapability, 7)

  def testMocaInterfaceMocaCtlFails(self):
    brcmmoca.PYNETIFCONF = MockPynet
    brcmmoca.MOCACTL = 'testdata/brcmmoca/mocactl_fail'
    moca = brcmmoca.BrcmMocaInterface(ifname='foo0', upstream=False)
    self.assertEqual(moca.FirmwareVersion, '0')
    self.assertEqual(moca.HighestVersion, '0.0')
    self.assertEqual(moca.CurrentVersion, '0.0')
    self.assertEqual(moca.BackupNC, '')
    self.assertFalse(moca.PrivacyEnabled)
    self.assertFalse(moca.QAM256Capable)
    self.assertEqual(moca.PacketAggregationCapability, 0)

  def testLastChange(self):
    brcmmoca.PYNETIFCONF = MockPynet
    moca = brcmmoca.BrcmMocaInterface(ifname='foo0', upstream=False)
    brcmmoca.MOCACTL = 'testdata/brcmmoca/mocactl_up1'
    self.assertEqual(moca.LastChange, 6090)
    brcmmoca.MOCACTL = 'testdata/brcmmoca/mocactl_up2'
    self.assertEqual(moca.LastChange, 119728800)

  def testAssociatedDevice(self):
    brcmmoca.MOCACTL = 'testdata/brcmmoca/mocactl'
    moca = brcmmoca.BrcmMocaInterface(ifname='foo0', upstream=False)
    self.assertEqual(2, moca.AssociatedDeviceNumberOfEntries)

    ad = moca.GetAssociatedDevice(0)
    ad.ValidateExports()
    self.assertEqual(ad.MACAddress, '00:01:00:11:23:33')
    self.assertEqual(ad.NodeID, 0)
    self.assertEqual(ad.PreferredNC, False)
    self.assertEqual(ad.PHYTxRate, 293)
    self.assertEqual(ad.PHYRxRate, 291)
    self.assertEqual(ad.TxPowerControlReduction, 3)
    self.assertEqual(ad.RxPowerLevel, 4)
    self.assertEqual(ad.TxBcastRate, 290)
    self.assertEqual(ad.RxBcastPowerLevel, 2)
    self.assertEqual(ad.TxPackets, 1)
    self.assertEqual(ad.RxPackets, 2)
    self.assertEqual(ad.RxErroredAndMissedPackets, 11)
    self.assertEqual(ad.QAM256Capable, True)
    self.assertEqual(ad.PacketAggregationCapability, 10)
    self.assertEqual(ad.RxSNR, 39)

    ad = moca.GetAssociatedDevice(1)
    ad.ValidateExports()
    self.assertEqual(ad.MACAddress, '00:01:00:11:23:44')
    self.assertEqual(ad.NodeID, 1)
    self.assertEqual(ad.PreferredNC, True)
    self.assertEqual(ad.PHYTxRate, 283)
    self.assertEqual(ad.PHYRxRate, 281)
    self.assertEqual(ad.TxPowerControlReduction, 2)
    self.assertEqual(ad.RxPowerLevel, 3)
    self.assertEqual(ad.TxBcastRate, 280)
    self.assertEqual(ad.RxBcastPowerLevel, 1)
    self.assertEqual(ad.TxPackets, 7)
    self.assertEqual(ad.RxPackets, 8)
    self.assertEqual(ad.RxErroredAndMissedPackets, 23)
    self.assertEqual(ad.QAM256Capable, False)
    self.assertEqual(ad.PacketAggregationCapability, 7)
    self.assertEqual(ad.RxSNR, 38)


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
