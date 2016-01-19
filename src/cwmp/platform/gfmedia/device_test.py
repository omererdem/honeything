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

"""Unit tests for device.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import unittest

import google3
import tornado.ioloop
import tornado.testing
import device


class MockIoloop(object):
  def __init__(self):
    self.timeout = None
    self.callback = None

  def add_timeout(self, timeout, callback, monotonic=None):
    self.timeout = timeout
    self.callback = callback


class DeviceTest(tornado.testing.AsyncTestCase):
  """Tests for device.py."""

  def setUp(self):
    super(DeviceTest, self).setUp()
    self.old_ACSCONNECTED = device.ACSCONNECTED
    self.old_CONFIGDIR = device.CONFIGDIR
    self.old_GINSTALL = device.GINSTALL
    self.old_HNVRAM = device.HNVRAM
    self.old_LEDSTATUS = device.LEDSTATUS
    self.old_NAND_MB = device.NAND_MB
    self.old_PROC_CPUINFO = device.PROC_CPUINFO
    self.old_REBOOT = device.REBOOT
    self.old_REPOMANIFEST = device.REPOMANIFEST
    self.old_SET_ACS = device.SET_ACS
    self.old_VERSIONFILE = device.VERSIONFILE
    self.install_cb_called = False
    self.install_cb_faultcode = None
    self.install_cb_faultstring = None

  def tearDown(self):
    super(DeviceTest, self).tearDown()
    device.ACSCONNECTED = self.old_ACSCONNECTED
    device.CONFIGDIR = self.old_CONFIGDIR
    device.GINSTALL = self.old_GINSTALL
    device.HNVRAM = self.old_HNVRAM
    device.LEDSTATUS = self.old_LEDSTATUS
    device.NAND_MB = self.old_NAND_MB
    device.PROC_CPUINFO = self.old_PROC_CPUINFO
    device.REBOOT = self.old_REBOOT
    device.REPOMANIFEST = self.old_REPOMANIFEST
    device.SET_ACS = self.old_SET_ACS
    device.VERSIONFILE = self.old_VERSIONFILE

  def testGetSerialNumber(self):
    did = device.DeviceId()
    device.HNVRAM = 'testdata/device/hnvram'
    self.assertEqual(did.SerialNumber, '123456789')

    device.HNVRAM = 'testdata/device/hnvramSN_Empty'
    self.assertEqual(did.SerialNumber, '000000000000')

    device.HNVRAM = 'testdata/device/hnvramSN_Err'
    self.assertEqual(did.SerialNumber, '000000000000')

  def testBadHnvram(self):
    did = device.DeviceId()
    device.HNVRAM = '/no_such_binary_at_this_path'
    self.assertEqual(did.SerialNumber, '000000000000')

  def testModelName(self):
    did = device.DeviceId()
    device.HNVRAM = 'testdata/device/hnvram'
    self.assertEqual(did.ModelName, 'ModelName')

  def testSoftwareVersion(self):
    did = device.DeviceId()
    device.VERSIONFILE = 'testdata/device/version'
    self.assertEqual(did.SoftwareVersion, '1.2.3')

  def testAdditionalSoftwareVersion(self):
    did = device.DeviceId()
    device.REPOMANIFEST = 'testdata/device/repomanifest'
    self.assertEqual(did.AdditionalSoftwareVersion,
                     'platform 1111111111111111111111111111111111111111')

  def testGetHardwareVersion(self):
    device.HNVRAM = 'testdata/device/hnvram'
    device.PROC_CPUINFO = 'testdata/device/proc_cpuinfo_b0'
    device.NAND_MB = 'testdata/device/nand_size_mb_rev1'
    did = device.DeviceId()
    self.assertEqual(did.HardwareVersion, 'rev')

    device.HNVRAM = 'testdata/device/hnvramFOO_Empty'
    self.assertEqual(did.HardwareVersion, '0')

    device.PROC_CPUINFO = 'testdata/device/proc_cpuinfo_b2'
    self.assertEqual(did.HardwareVersion, '1')

    device.NAND_MB = 'testdata/device/nand_size_mb_rev2'
    self.assertEqual(did.HardwareVersion, '2')

    device.NAND_MB = 'testdata/device/nand_size_mb_unk'
    self.assertEqual(did.HardwareVersion, '?')

  def testFanSpeed(self):
    fan = device.FanReadGpio(speed_filename='testdata/fanspeed',
                    percent_filename='testdata/fanpercent')
    fan.ValidateExports()
    self.assertEqual(fan.RPM, 1800)
    self.assertEqual(fan.DesiredPercentage, 50)
    fan = device.FanReadGpio(speed_filename='foo',
                    percent_filename='bar')
    self.assertEqual(fan.RPM, -1)
    self.assertEqual(fan.DesiredPercentage, -1)

  def install_callback(self, faultcode, faultstring, must_reboot):
    self.install_cb_called = True
    self.install_cb_faultcode = faultcode
    self.install_cb_faultstring = faultstring
    self.install_cb_must_reboot = must_reboot
    self.stop()

  def testBadInstaller(self):
    device.GINSTALL = '/dev/null'
    inst = device.Installer('/dev/null', ioloop=self.io_loop)
    inst.install(file_type='1 Firmware Upgrade Image',
                 target_filename='',
                 callback=self.install_callback)
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testInstallerStdout(self):
    device.GINSTALL = 'testdata/device/installer_128k_stdout'
    inst = device.Installer('testdata/device/imagefile', ioloop=self.io_loop)
    inst.install(file_type='1 Firmware Upgrade Image',
                 target_filename='',
                 callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 0)
    self.assertFalse(self.install_cb_faultstring)
    self.assertTrue(self.install_cb_must_reboot)

  def testInstallerFailed(self):
    device.GINSTALL = 'testdata/device/installer_fails'
    inst = device.Installer('testdata/device/imagefile', ioloop=self.io_loop)
    inst.install(file_type='1 Firmware Upgrade Image',
                 target_filename='',
                 callback=self.install_callback)
    self.wait()
    self.assertTrue(self.install_cb_called)
    self.assertEqual(self.install_cb_faultcode, 9002)
    self.assertTrue(self.install_cb_faultstring)

  def testSetAcs(self):
    device.SET_ACS = 'testdata/device/set-acs'
    scriptout = tempfile.NamedTemporaryFile()
    os.environ['TESTOUTPUT'] = scriptout.name
    pc = device.PlatformConfig(ioloop=MockIoloop())
    self.assertEqual(pc.GetAcsUrl(), 'bar')
    pc.SetAcsUrl('foo')
    self.assertEqual(scriptout.read().strip(), 'cwmp foo')

  def testClearAcs(self):
    device.SET_ACS = 'testdata/device/set-acs'
    scriptout = tempfile.NamedTemporaryFile()
    os.environ['TESTOUTPUT'] = scriptout.name
    pc = device.PlatformConfig(ioloop=MockIoloop())
    pc.SetAcsUrl('')
    self.assertEqual(scriptout.read().strip(), 'cwmp clear')

  def testAcsAccess(self):
    device.SET_ACS = 'testdata/device/set-acs'
    scriptout = tempfile.NamedTemporaryFile()
    os.environ['TESTOUTPUT'] = scriptout.name
    ioloop = MockIoloop()
    tmpdir = tempfile.mkdtemp()
    tmpfile = os.path.join(tmpdir, 'acsconnected')
    self.assertRaises(OSError, os.stat, tmpfile)  # File does not exist yet
    device.ACSCONNECTED = tmpfile
    pc = device.PlatformConfig(ioloop)
    acsurl = 'this is the acs url'

    # Simulate ACS connection
    pc.AcsAccessAttempt(acsurl)
    pc.AcsAccessSuccess(acsurl)
    self.assertTrue(os.stat(tmpfile))
    self.assertEqual(open(tmpfile, 'r').read(), acsurl)
    self.assertTrue(ioloop.timeout)
    self.assertTrue(ioloop.callback)

    # Simulate timeout
    pc.AcsAccessAttempt(acsurl)
    scriptout.truncate()
    ioloop.callback()
    self.assertRaises(OSError, os.stat, tmpfile)
    self.assertEqual(scriptout.read().strip(), 'timeout ' + acsurl)

    # cleanup
    shutil.rmtree(tmpdir)


if __name__ == '__main__':
  unittest.main()
