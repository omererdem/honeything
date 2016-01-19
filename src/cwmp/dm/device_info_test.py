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

"""Unit tests for tr-181 DeviceInfo implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import unittest

import google3
import tr.core
import device_info
import tornado.testing


class TestDeviceId(device_info.DeviceIdMeta):
  def Manufacturer(self):
    return 'Manufacturer'

  def ManufacturerOUI(self):
    return '000000'

  def ModelName(self):
    return 'ModelName'

  def Description(self):
    return 'Description'

  def SerialNumber(self):
    return '00000000'

  def HardwareVersion(self):
    return '0'

  def AdditionalHardwareVersion(self):
    return '0'

  def SoftwareVersion(self):
    return '0'

  def AdditionalSoftwareVersion(self):
    return '0'

  def ProductClass(self):
    return 'ProductClass'

  def ModemFirmwareVersion(self):
    return 'ModemFirmwareVersion'


fake_periodics = []
class FakePeriodicCallback(object):
  def __init__(self, callback, callback_time, io_loop=None):
    self.callback = callback
    self.callback_time = callback_time
    self.io_loop = io_loop
    self.start_called = False
    self.stop_called = False
    fake_periodics.append(self)

  def start(self):
    self.start_called = True

  def stop(self):
    self.stop_called = True


def FakeLedStatus():
  return 'LEDSTATUS'


class DeviceInfoTest(tornado.testing.AsyncTestCase):
  """Tests for device_info.py."""

  def setUp(self):
    super(DeviceInfoTest, self).setUp()
    self.old_PERIODICCALL = device_info.PERIODICCALL
    self.old_PROC_MEMINFO = device_info.PROC_MEMINFO
    self.old_PROC_NET_DEV = device_info.PROC_NET_DEV
    self.old_PROC_UPTIME = device_info.PROC_UPTIME
    self.old_SLASH_PROC = device_info.SLASH_PROC
    device_info.PERIODICCALL = FakePeriodicCallback
    device_info.PROC_MEMINFO = 'testdata/device_info/meminfo'
    device_info.PROC_UPTIME = 'testdata/device_info/uptime'
    device_info.SLASH_PROC = 'testdata/device_info/processes'

  def tearDown(self):
    super(DeviceInfoTest, self).tearDown()
    device_info.PERIODICCALL = self.old_PERIODICCALL
    device_info.PROC_MEMINFO = self.old_PROC_MEMINFO
    device_info.PROC_NET_DEV = self.old_PROC_NET_DEV
    device_info.PROC_UPTIME = self.old_PROC_UPTIME
    device_info.SLASH_PROC = self.old_SLASH_PROC

  def testValidate181(self):
    di = device_info.DeviceInfo181Linux26(TestDeviceId())
    di.ValidateExports()

  def testValidate98(self):
    di = device_info.DeviceInfo98Linux26(TestDeviceId())
    di.ValidateExports()

  def testUptimeSuccess(self):
    device_info.PROC_UPTIME = 'testdata/device_info/uptime'
    di = device_info.DeviceInfo181Linux26(TestDeviceId())
    self.assertEqual(di.UpTime, '123')

  def testDeviceId(self):
    did = TestDeviceId()
    di = device_info.DeviceInfo181Linux26(did)
    self.assertEqual(did.Manufacturer, di.Manufacturer)
    self.assertEqual(did.ManufacturerOUI, di.ManufacturerOUI)
    self.assertEqual(did.ModelName, di.ModelName)
    self.assertEqual(did.Description, di.Description)
    self.assertEqual(did.SerialNumber, di.SerialNumber)
    self.assertEqual(did.HardwareVersion, di.HardwareVersion)
    self.assertEqual(did.AdditionalHardwareVersion,
                     di.AdditionalHardwareVersion)
    self.assertEqual(did.SoftwareVersion, di.SoftwareVersion)
    self.assertEqual(did.AdditionalSoftwareVersion,
                     di.AdditionalSoftwareVersion)
    self.assertEqual(did.ProductClass, di.ProductClass)

  def testMemoryStatusSuccess(self):
    device_info.PROC_MEMINFO = 'testdata/device_info/meminfo'
    mi = device_info.MemoryStatusLinux26()
    self.assertEqual(mi.Total, 123456)
    self.assertEqual(mi.Free, 654321)

  def testMemoryStatusTotal(self):
    device_info.PROC_MEMINFO = 'testdata/device_info/meminfo_total'
    mi = device_info.MemoryStatusLinux26()
    self.assertEqual(mi.Total, 123456)
    self.assertEqual(mi.Free, 0)

  def testMemoryStatusFree(self):
    device_info.PROC_MEMINFO = 'testdata/device_info/meminfo_free'
    mi = device_info.MemoryStatusLinux26()
    self.assertEqual(mi.Total, 0)
    self.assertEqual(mi.Free, 654321)

  def testCPUUsage(self):
    ps = device_info.ProcessStatusLinux26(self.io_loop)
    self.assertEqual(len(fake_periodics), 1)
    self.assertTrue(fake_periodics[0].start_called)
    device_info.PROC_STAT = 'testdata/device_info/cpu/stat0'
    self.assertEqual(ps.CPUUsage, 0)
    fake_periodics[0].callback()  # simulate periodic timer
    self.assertEqual(ps.CPUUsage, 0)
    device_info.PROC_STAT = 'testdata/device_info/cpu/stat'
    fake_periodics[0].callback()  # simulate periodic timer
    self.assertEqual(ps.CPUUsage, 10)
    del fake_periodics[0]

  def testProcessStatusReal(self):
    ps = device_info.ProcessStatusLinux26(self.io_loop)
    # This fetches the processes running on the unit test machine. We can't
    # make many assertions about this, just that there should be some processes
    # running.
    processes = ps.ProcessList
    if os.path.exists('/proc/status'):  # otherwise not a Linux machine
      self.assertTrue(processes)

  def testProcessStatusFakeData(self):
    Process = device_info.BASE181DEVICE.DeviceInfo.ProcessStatus.Process
    fake_processes = {
        1: Process(PID=1, Command='init', Size=551,
                     Priority=20, CPUTime=81970,
                     State='Sleeping'),
        3: Process(PID=3, Command='migration/0', Size=0,
                     Priority=-100, CPUTime=591510,
                     State='Stopped'),
        5: Process(PID=5, Command='foobar', Size=0,
                     Priority=-100, CPUTime=591510,
                     State='Zombie'),
        17: Process(PID=17, Command='bar', Size=0,
                      Priority=-100, CPUTime=591510,
                      State='Uninterruptible'),
        164: Process(PID=164, Command='udevd', Size=288,
                       Priority=16, CPUTime=300,
                       State='Running'),
        770: Process(PID=770, Command='automount', Size=6081,
                       Priority=20, CPUTime=5515790,
                       State='Uninterruptible')
        }
    device_info.SLASH_PROC = 'testdata/device_info/processes'
    ps = device_info.ProcessStatusLinux26(self.io_loop)
    processes = ps.ProcessList
    self.assertEqual(len(processes), 6)
    for p in processes.values():
      fake_p = fake_processes[p.PID]
      self.assertEqual(tr.core.Dump(fake_p), tr.core.Dump(p))

  def testProcessExited(self):
    device_info.SLASH_PROC = 'testdata/device_info/processes'
    ps = device_info.ProcessStatusLinux26(self.io_loop)
    proc = ps.GetProcess(1000)
    self.assertEqual(proc.PID, 1000);
    self.assertEqual(proc.Command, '<exited>');
    self.assertEqual(proc.Size, 0);
    self.assertEqual(proc.Priority, 0);
    self.assertEqual(proc.CPUTime, 0);
    self.assertEqual(proc.State, 'X_CATAWAMPUS-ORG_Exited');

  def testLedStatus(self):
    led = device_info.LedStatusReadFromFile(
        'LED', 'testdata/device_info/ledstatus')
    led.ValidateExports()
    self.assertEqual(led.Name, 'LED')
    self.assertEqual(led.Status, 'LED_ON')


if __name__ == '__main__':
  unittest.main()
