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

"""Unit tests for brcmwifi.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import stat
import tempfile
import unittest

import google3
import brcmwifi
import netdev


class BrcmWifiTest(unittest.TestCase):
  def setUp(self):
    self.old_WL_EXE = brcmwifi.WL_EXE
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlempty'
    brcmwifi.WL_SLEEP = 0
    brcmwifi.WL_AUTOCHAN_SLEEP = 0
    self.old_PROC_NET_DEV = netdev.PROC_NET_DEV
    self.files_to_remove = list()

  def tearDown(self):
    brcmwifi.WL_EXE = self.old_WL_EXE
    netdev.PROC_NET_DEV = self.old_PROC_NET_DEV
    for f in self.files_to_remove:
      os.remove(f)

  def MakeTestScript(self):
    """Create a script in /tmp, with an output file."""
    scriptfile = tempfile.NamedTemporaryFile(mode='r+', delete=False)
    os.chmod(scriptfile.name, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    outfile = tempfile.NamedTemporaryFile(delete=False)
    text = '#!/bin/sh\necho $* >> {0}'.format(outfile.name)
    scriptfile.write(text)
    scriptfile.close()  # Linux won't run it if text file is busy
    self.files_to_remove.append(scriptfile.name)
    self.files_to_remove.append(outfile.name)
    return (scriptfile, outfile)

  def RmFromList(self, l, item):
    try:
      l.remove('-i wifi0 ' + item)
      return True
    except ValueError:
      return False

  def VerifyCommonWlCommands(self, cmd, rmwep=0, wsec=0, primary_key=1,
                             wpa_auth=0, sup_wpa=1, amode='open',
                             autochan=True):
    # Verify the number of "rmwep #" commands, and remove them.
    l = [x for x in cmd.split('\n') if x]  # Suppress blank lines
    for i in range(rmwep, 4):
      self.assertTrue(self.RmFromList(l, 'rmwep %d' % i))
    self.assertTrue(self.RmFromList(l, 'wsec %d' % wsec))
    self.assertTrue(self.RmFromList(l, 'sup_wpa %d' % sup_wpa))
    self.assertTrue(self.RmFromList(l, 'wpa_auth %d' % wpa_auth))
    self.assertTrue(self.RmFromList(l, 'primary_key %d' % primary_key))
    self.assertTrue(self.RmFromList(l, 'radio on'))
    self.assertTrue(self.RmFromList(l, 'ap 1'))
    self.assertTrue(self.RmFromList(l, 'bss down'))
    if autochan:
      self.assertTrue(self.RmFromList(l, 'down'))
      self.assertTrue(self.RmFromList(l, 'spect 0'))
      self.assertTrue(self.RmFromList(l, 'mpc 0'))
      self.assertTrue(self.RmFromList(l, 'up'))
      self.assertTrue(self.RmFromList(l, 'ssid'))
      self.assertTrue(self.RmFromList(l, 'autochannel 1'))
      self.assertTrue(self.RmFromList(l, 'autochannel 2'))
      self.assertTrue(self.RmFromList(l, 'down'))
      self.assertTrue(self.RmFromList(l, 'spect 1'))
      self.assertTrue(self.RmFromList(l, 'mpc 1'))
    return l

  def testValidateExports(self):
    netdev.PROC_NET_DEV = 'testdata/brcmwifi/proc_net_dev'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.ValidateExports()
    stats = brcmwifi.BrcmWlanConfigurationStats('wifi0')
    stats.ValidateExports()

  def testCounters(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlcounters'
    wl = brcmwifi.Wl('foo0')
    counters = wl.GetWlCounters()
    self.assertEqual(counters['rxrtsocast'], '93')
    self.assertEqual(counters['d11_txfrmsnt'], '0')
    self.assertEqual(counters['txfunfl'], ['59', '60', '61', '62', '63', '64'])

  def testStatus(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlbssup'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.Status, 'Up')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlbssdown'
    self.assertEqual(bw.Status, 'Disabled')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlbsserr'
    self.assertEqual(bw.Status, 'Error')

  def testChannel(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlchannel'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.Channel, 1)

  def testValidateChannel(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlchannel'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertRaises(ValueError, bw.SetChannel, '166')
    self.assertRaises(ValueError, bw.SetChannel, '14')
    self.assertRaises(ValueError, bw.SetChannel, '0')
    self.assertRaises(ValueError, bw.SetChannel, '20')

  def testSetChannel(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.StartTransaction()
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    bw.Channel = '11'
    bw.CommitTransaction()
    output = out.read()
    out.close()
    outlist = self.VerifyCommonWlCommands(output, autochan=False)
    self.assertTrue(self.RmFromList(outlist, 'channel 11'))
    self.assertFalse(outlist)

  def testPossibleChannels(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlchannels'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.PossibleChannels,
                     '1-11,36,40,44,48,52,56,60,64,100,104,108,112,116,120,124,'
                     '128,132,136,140,149,153,157,161,165')

  def testSSID(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlssid'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.SSID, 'MySSID')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlssidempty'
    self.assertEqual(bw.SSID, '')

  def testValidateSSID(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlssid'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.SSID = r'myssid'
    bw.SSID = r'my ssid'  # A ValueError will fail the test here.
    self.assertRaises(ValueError, bw.SetSSID,
        r'myssidiswaaaaaaaaaaaaaaaaaytoolongtovalidate')

  def testSetSSID(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.StartTransaction()
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()
    bw.SSID = 'myssid'
    bw.CommitTransaction()
    output = out.read()
    out.close()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'up'))
    self.assertTrue(self.RmFromList(outlist, 'ssid myssid'))
    self.assertFalse(outlist)

  def testInvalidSSID(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertRaises(ValueError, bw.SetSSID,
                      'abcdefghijklmnopqrstuvwxyz0123456789'
                      'abcdefghijklmnopqrstuvwxyz0123456789')

  def testBSSID(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlbssid'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.BSSID, '01:23:45:67:89:ab')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlempty'
    self.assertEqual(bw.BSSID, '00:00:00:00:00:00')

  def testValidateBSSID(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertRaises(ValueError, bw.SetBSSID, 'This is not a BSSID.')
    self.assertRaises(ValueError, bw.SetBSSID, '00:00:00:00:00:00')
    self.assertRaises(ValueError, bw.SetBSSID, 'ff:ff:ff:ff:ff:ff')

  def testSetBSSID(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.StartTransaction()
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()
    bw.BSSID = '00:99:aa:bb:cc:dd'
    bw.CommitTransaction()
    output = out.read()
    out.close()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'bssid 00:99:aa:bb:cc:dd'))
    self.assertFalse(outlist)

  def testRegulatoryDomain(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlcountry.us'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.RegulatoryDomain, 'US')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlcountry.jp'
    self.assertEqual(bw.RegulatoryDomain, 'JP')

  def testInvalidRegulatoryDomain(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlcountrylist'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertRaises(ValueError, bw.SetRegulatoryDomain, 'ZZ')
    self.assertRaises(ValueError, bw.SetRegulatoryDomain, '')

  def testSetRegulatoryDomain(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlcountrylist'
    bw.StartTransaction()
    bw.RegulatoryDomain = 'US'
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.Enable = 'True'
    out.truncate()
    bw.RadioEnabled = 'True'
    bw.CommitTransaction()
    output = out.read()
    out.close()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'country US'))
    self.assertFalse(outlist)

  def testBasicRateSet(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlrateset'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.BasicDataTransmitRates, '1,2,5.5,11')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlrateset2'
    self.assertEqual(bw.BasicDataTransmitRates, '1,2,5.5,11,16.445')

  def testOperationalRateSet(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlrateset'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.OperationalDataTransmitRates,
                     '1,2,5.5,6,9,11,12,18,24,36,48,54')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlrateset2'
    self.assertEqual(bw.OperationalDataTransmitRates, '1,2,5.5,7.5,11,16.445')

  def testTransmitPower(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlpwrpercent'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.TransmitPower, '25')

  def testValidateTransmitPower(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertRaises(ValueError, bw.SetTransmitPower, '101')
    self.assertRaises(ValueError, bw.SetTransmitPower, 'foo')

  def testSetTransmitPower(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.StartTransaction()
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()
    bw.TransmitPower = '77'
    bw.CommitTransaction()
    output = out.read()
    out.close()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'pwr_percent 77'))
    self.assertFalse(outlist)

  def testTransmitPowerSupported(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.TransmitPowerSupported, '1-100')

  def testAutoRateFallBackEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlinterference0'
    self.assertFalse(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlinterference1'
    self.assertFalse(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlinterference2'
    self.assertFalse(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlinterference3'
    self.assertTrue(bw.AutoRateFallBackEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlinterference4'
    self.assertTrue(bw.AutoRateFallBackEnabled)

  def testSetAutoRateFallBackEnabled(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.StartTransaction()
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()

    bw.AutoRateFallBackEnabled = 'True'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'interference 4'))
    self.assertFalse(outlist)
    out.truncate()
    bw.StartTransaction()
    bw.AutoRateFallBackEnabled = 'False'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output)
    out.close()
    self.assertTrue(self.RmFromList(outlist, 'interference 3'))
    self.assertFalse(outlist)

  def testSSIDAdvertisementEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlclosed0'
    self.assertTrue(bw.SSIDAdvertisementEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlclosed1'
    self.assertFalse(bw.SSIDAdvertisementEnabled)

  def testSetSSIDAdvertisementEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.StartTransaction()
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    out.truncate()
    bw.SSIDAdvertisementEnabled = 'True'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertTrue(self.RmFromList(outlist, 'closed 0'))
    self.assertFalse(outlist)
    out.truncate()
    bw.StartTransaction()
    bw.SSIDAdvertisementEnabled = 'False'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output)
    out.close()
    self.assertTrue(self.RmFromList(outlist, 'closed 1'))
    self.assertFalse(outlist)

  def testRadioEnabled(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlradiooff'
    self.assertFalse(bw.RadioEnabled)
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlradioon'
    self.assertTrue(bw.RadioEnabled)

  def testSetRadioEnabled(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.StartTransaction()
    bw.Enable = 'True'
    out.truncate()
    bw.RadioEnabled = 'True'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output)
    self.assertFalse(outlist)
    out.truncate()
    bw.StartTransaction()
    bw.RadioEnabled = 'False'
    bw.CommitTransaction()
    output = out.read()
    out.close()
    self.assertEqual(output, '-i wifi0 radio off\n')

  def testNoEnable(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.Enable = 'False'
    output = out.read()
    out.close()
    self.assertFalse(output)
    self.assertFalse(bw.Enable)

  def testInvalidBooleans(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertRaises(ValueError, bw.SetAutoRateFallBackEnabled, 'InvalidBool')
    self.assertRaises(ValueError, bw.SetEnable, 'InvalidBool')
    self.assertRaises(ValueError, bw.SetRadioEnabled, 'InvalidBool')
    self.assertRaises(ValueError, bw.SetSSIDAdvertisementEnabled, 'InvalidBool')

  def testEncryptionModes(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec0'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'X_CATAWAMPUS-ORG_None')
    self.assertEqual(bw.WPAEncryptionModes, 'X_CATAWAMPUS-ORG_None')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec1'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'WEPEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'WEPEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec2'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'TKIPEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'TKIPEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec3'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'WEPandTKIPEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'WEPandTKIPEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec4'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'AESEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'AESEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec5'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'WEPandAESEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'WEPandAESEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec6'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'TKIPandAESEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'TKIPandAESEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec7'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'WEPandTKIPandAESEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'WEPandTKIPandAESEncryption')
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlwsec15'
    self.assertEqual(bw.IEEE11iEncryptionModes, 'WEPandTKIPandAESEncryption')
    self.assertEqual(bw.WPAEncryptionModes, 'WEPandTKIPandAESEncryption')

  def testInvalidEncryptionModes(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertRaises(ValueError, bw.SetBasicEncryptionModes, 'invalid')
    self.assertRaises(ValueError, bw.SetIEEE11iEncryptionModes, 'invalid')
    self.assertRaises(ValueError, bw.SetWPAEncryptionModes, 'invalid')

  def testInvalidBeaconType(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertRaises(ValueError, bw.SetBeaconType, 'FooFi')

  def testAuthenticationMode(self):
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertRaises(ValueError, bw.SetBasicAuthenticationMode, 'Invalid')
    bw.BasicAuthenticationMode = 'None'
    bw.BasicAuthenticationMode = 'SharedAuthentication'
    self.assertRaises(ValueError, bw.SetIEEE11iAuthenticationMode, 'Invalid')
    bw.IEEE11iAuthenticationMode = 'PSKAuthentication'
    self.assertRaises(ValueError, bw.SetWPAAuthenticationMode, 'Invalid')
    bw.WPAAuthenticationMode = 'PSKAuthentication'

  def testSetBeaconType(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.StartTransaction()
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    bw.BasicEncryptionModes = 'None' # wsec 0
    bw.WPAEncryptionModes = 'TKIPEncryption'  # wsec 2
    bw.WPAAuthenticationMode = 'PSKAuthentication'
    bw.IEEE11iEncryptionModes = 'AESEncryption'  # wsec 4
    bw.IEEE11iAuthenticationMode = 'PSKAuthentication'
    bw.BeaconType = 'None'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=0, sup_wpa=0)
    self.assertFalse(outlist)
    out.truncate()

    bw.StartTransaction()
    bw.BeaconType = 'Basic'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=0, sup_wpa=0)
    self.assertFalse(outlist)
    out.truncate()

    bw.StartTransaction()
    bw.BasicEncryptionModes = 'WEPEncryption' # wsec 1
    bw.BeaconType = 'Basic'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=1, sup_wpa=0)
    self.assertFalse(outlist)
    out.truncate()

    bw.StartTransaction()
    bw.BasicAuthenticationMode = 'SharedAuthentication'
    bw.BasicEncryptionModes = 'WEPEncryption' # wsec 1
    bw.BeaconType = 'Basic'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=1, sup_wpa=0)
    self.assertFalse(outlist)
    out.truncate()

    bw.StartTransaction()
    bw.BeaconType = 'WPA'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=2, wpa_auth=4)
    self.assertFalse(outlist)
    out.truncate()

    bw.StartTransaction()
    bw.BeaconType = '11i'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=4, wpa_auth=128)
    self.assertFalse(outlist)
    out.truncate()

    # NOTE(jnewlin): I do not believe we should support these beacon types
    # below.
    bw.StartTransaction()
    bw.BeaconType = 'BasicandWPA'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=2, wpa_auth=4)
    self.assertFalse(outlist)
    out.truncate()

    bw.StartTransaction()
    bw.BeaconType = 'Basicand11i'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=4, wpa_auth=128)
    self.assertFalse(outlist)
    out.truncate()

    bw.StartTransaction()
    bw.BeaconType = 'WPAand11i'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=4, wpa_auth=128)
    self.assertFalse(outlist)
    out.truncate()

    bw.StartTransaction()
    bw.BeaconType = 'BasicandWPAand11i'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wsec=4, wpa_auth=128)
    self.assertFalse(outlist)
    out.truncate()

  def testAuthenticationModes(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.StartTransaction()
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, wpa_auth=0)
    self.assertFalse(outlist)
    out.truncate()

    # Test WEP
    bw.StartTransaction()
    bw.BeaconType = 'Basic'
    bw.BasicAuthenticationMode = 'None'
    bw.BasicEncryptionModes = 'WEPEncryption'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, sup_wpa=0, wpa_auth=0, wsec=1)
    self.assertFalse(outlist)

    # Test WPA-TKIP
    bw.StartTransaction()
    bw.BeaconType = 'WPA'
    bw.WPAAuthenticationMode = 'PSKAuthentication'
    bw.WPAEncryptionModes = 'TKIPEncryption'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, sup_wpa=1, wpa_auth=4, wsec=2)
    self.assertFalse(outlist)
    out.truncate()

    # Test WPA2-AES
    bw.StartTransaction()
    bw.BeaconType = '11i'
    bw.IEEE11iAuthenticationMode = 'PSKAuthentication'
    bw.IEEE11iEncryptionModes = 'AESEncryption'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, sup_wpa=1, wpa_auth=128, wsec=4)
    self.assertFalse(outlist)
    out.truncate()

  def testWepKey(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.StartTransaction()
    bw.Enable = 'True'
    bw.WEPKeyList[1].WEPKey = 'password1'
    bw.WEPKeyList[2].WEPKey = 'password2'
    bw.WEPKeyList[3].WEPKey = 'password3'
    bw.WEPKeyList[4].WEPKey = 'password4'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, rmwep=4, wsec=0)
    self.assertTrue(self.RmFromList(outlist, 'addwep 0 password1'))
    self.assertTrue(self.RmFromList(outlist, 'addwep 1 password2'))
    self.assertTrue(self.RmFromList(outlist, 'addwep 2 password3'))
    self.assertTrue(self.RmFromList(outlist, 'addwep 3 password4'))
    print outlist
    self.assertFalse(outlist)

  def testPreSharedKey(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.StartTransaction()
    bw.Enable = 'True'
    bw.PreSharedKeyList[1].PreSharedKey = 'password1'
    bw.CommitTransaction()
    output = out.read()
    outlist = self.VerifyCommonWlCommands(output, rmwep=0, wsec=0)
    self.assertTrue(self.RmFromList(outlist, 'set_pmk password1'))
    self.assertFalse(outlist)

  def testStats(self):
    netdev.PROC_NET_DEV = 'testdata/brcmwifi/proc_net_dev'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    stats = bw.Stats
    stats.ValidateExports()
    # pylint: disable-msg=E1101
    self.assertEqual(stats.BroadcastPacketsReceived, None)
    self.assertEqual(stats.BroadcastPacketsSent, None)
    self.assertEqual(stats.BytesReceived, '1')
    self.assertEqual(stats.BytesSent, '9')
    self.assertEqual(stats.DiscardPacketsReceived, '4')
    self.assertEqual(stats.DiscardPacketsSent, '11')
    self.assertEqual(stats.ErrorsReceived, '9')
    self.assertEqual(stats.ErrorsSent, '12')
    self.assertEqual(stats.MulticastPacketsReceived, '8')
    self.assertEqual(stats.MulticastPacketsSent, None)
    self.assertEqual(stats.PacketsReceived, '100')
    self.assertEqual(stats.PacketsSent, '10')
    self.assertEqual(stats.UnicastPacketsReceived, '92')
    self.assertEqual(stats.UnicastPacketsSent, '10')
    self.assertEqual(stats.UnknownProtoPacketsReceived, None)

  def testAssociatedDevice(self):
    brcmwifi.WL_EXE = 'testdata/brcmwifi/wlassociated'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    self.assertEqual(bw.TotalAssociations, 3)
    speeds = {'a0:b0:c0:00:00:01': '1',
              'a0:b0:c0:00:00:02': '2',
              'a0:b0:c0:00:00:03': '3'}
    auth = {'a0:b0:c0:00:00:01': True,
            'a0:b0:c0:00:00:02': False,
            'a0:b0:c0:00:00:03': True}
    seen = set()
    for ad in bw.AssociatedDeviceList.values():
      ad.ValidateExports()
      mac = ad.AssociatedDeviceMACAddress.lower()
      self.assertEqual(ad.LastDataTransmitRate, speeds[mac])
      self.assertEqual(ad.AssociatedDeviceAuthenticationState, auth[mac])
      seen.add(mac)
    self.assertEqual(len(seen), 3)

  def testKeyPassphrase(self):
    netdev.PROC_NET_DEV = 'testdata/brcmwifi/proc_net_dev'
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.KeyPassphrase = 'testpassword'
    self.assertEqual(bw.KeyPassphrase, bw.PreSharedKeyList[1].KeyPassphrase)

  def testAutoChannel(self):
    (script, out) = self.MakeTestScript()
    brcmwifi.WL_EXE = script.name
    bw = brcmwifi.BrcmWifiWlanConfiguration('wifi0')
    bw.StartTransaction()
    bw.Enable = 'True'
    bw.RadioEnabled = 'True'
    bw.AutoChannelEnable = 'True'
    out.truncate()
    bw.CommitTransaction()
    output = out.read()
    out.close()
    # AutoChannel changes the order of the initial commands
    # slightly.
    outlist = [x for x in output.split('\n') if x]
    self.assertEqual(outlist[0], '-i wifi0 radio on')
    self.assertEqual(outlist[1], '-i wifi0 ap 1')
    self.assertEqual(outlist[2], '-i wifi0 down')
    self.assertTrue(self.RmFromList(outlist, 'spect 0'))
    self.assertTrue(self.RmFromList(outlist, 'mpc 0'))
    self.assertTrue(self.RmFromList(outlist, 'up'))
    self.assertTrue(self.RmFromList(outlist, 'ssid'))
    self.assertTrue(self.RmFromList(outlist, 'autochannel 1'))
    self.assertTrue(self.RmFromList(outlist, 'autochannel 2'))
    self.assertTrue(self.RmFromList(outlist, 'down'))
    self.assertTrue(self.RmFromList(outlist, 'mpc 1'))
    self.assertTrue(self.RmFromList(outlist, 'spect 1'))

if __name__ == '__main__':
  unittest.main()
