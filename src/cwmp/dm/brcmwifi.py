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

# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409

"""Implementation of tr-98/181 WLAN objects for Broadcom Wifi chipsets.

The platform code is expected to set the BSSID (which is really a MAC address).
The Wifi module should be populated with a MAC address. For example if it
appears as eth2, then "ifconfig eth2" will show the MAC address from the Wifi
card. The platform should execute:
  wl bssid xx:xx:xx:xx:xx:xx
To set the bssid to the desired MAC address, either the one from the wifi
card or your own.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import collections
import copy
import re
import subprocess
import time
import tr.core
import tr.cwmpbool
import tr.tr098_v1_4
import netdev
import wifi

BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
BASE98WIFI = BASE98IGD.LANDevice.WLANConfiguration

# Supported Encryption Modes
EM_NONE = 0
EM_WEP = 1
EM_TKIP = 2
EM_AES = 4
EM_WSEC = 8  # Not enumerated in tr-98
EM_FIPS = 0x80  # Not enumerated in tr-98
EM_WAPI = 0x100  # Not enumerated in tr-98

# Unit tests can override these.
WL_EXE = '/usr/bin/wl'
WL_SLEEP = 3  # Broadcom recommendation for 3 second sleep before final join.
# Broadcom recommendation for delay while scanning for a channel
WL_AUTOCHAN_SLEEP = 2

# Parameter enumerations
BEACONS = frozenset(['None', 'Basic', 'WPA', '11i', 'BasicandWPA',
                     'Basicand11i', 'WPAand11i', 'BasicandWPAand11i'])
BASICENCRYPTIONS = frozenset(['None', 'WEPEncryption'])
# We do not support EAPAuthentication
BASICAUTHMODES = frozenset(['None', 'SharedAuthentication'])
WPAAUTHMODES = frozenset(['PSKAuthentication'])


def IsInteger(value):
  try:
    int(value)
  except:  #pylint: disable-msg=W0702
    return False
  return True


class WifiConfig(object):
  """A dumb data object to store config settings."""
  pass


class Wl(object):
  """Class wrapping Broadcom's wl utility.

  This class implements low-level wifi handling, the stuff which tr-98
  and tr-181 can both take advantage of.

  This object cannot retain any state about the Wifi configuration, as
  both tr-98 and tr-181 can have instances of this object. It has to
  consult the wl utility for all state information."""

  def __init__(self, interface):
    self._if = interface

  def _SubprocessCall(self, cmd):
    subprocess.check_call([WL_EXE, '-i', self._if] + cmd)

  def _SubprocessWithOutput(self, cmd):
    wl = subprocess.Popen([WL_EXE, '-i', self._if] + cmd,
                          stdout=subprocess.PIPE)
    out, _ = wl.communicate(None)
    return out

  def GetWlCounters(self):
    out = self._SubprocessWithOutput(['counters'])

    # match three different types of stat output:
    # rxuflo: 1 2 3 4 5 6
    # rxfilter 1
    # d11_txretrie
    st = re.compile('(\w+:?(?: \d+)*)')

    stats = st.findall(out)
    r1 = re.compile('(\w+): (.+)')
    r2 = re.compile('(\w+) (\d+)')
    r3 = re.compile('(\w+)')
    sdict = dict()
    for stat in stats:
      p1 = r1.match(stat)
      p2 = r2.match(stat)
      p3 = r3.match(stat)
      if p1 is not None:
        sdict[p1.group(1).lower()] = p1.group(2).split()
      elif p2 is not None:
        sdict[p2.group(1).lower()] = p2.group(2)
      elif p3 is not None:
        sdict[p3.group(1).lower()] = '0'
    return sdict

  def DoAutoChannelSelect(self):
    """Run the AP through an auto channel selection."""
    # Make sure the interface is up, and ssid is the empty string.
    self._SubprocessCall(['down'])
    self._SubprocessCall(['spect', '0'])
    self._SubprocessCall(['mpc', '0'])
    self._SubprocessCall(['up'])
    self._SubprocessCall(['ssid', ''])
    time.sleep(WL_SLEEP)
    # This starts a scan, and we give it some time to complete.
    # TODO(jnewlin): Chat with broadcom about how long we need/should
    # wait before setting the autoscanned channel.
    self._SubprocessCall(['autochannel', '1'])
    time.sleep(WL_AUTOCHAN_SLEEP)
    # This programs the channel with the best channel found during the
    # scan.
    self._SubprocessCall(['autochannel', '2'])
    # Bring the interface back down and reset spect and mpc settings.
    # spect can't be changed for 0 -> 1 unless the interface is down.
    self._SubprocessCall(['down'])
    self._SubprocessCall(['spect', '1'])
    self._SubprocessCall(['mpc', '1'])

  def SetApMode(self):
    """Put device into AP mode."""
    self._SubprocessCall(['ap', '1'])

  def GetAssociatedDevices(self):
    """Return a list of MAC addresses of associated STAs."""
    out = self._SubprocessWithOutput(['assoclist'])
    stamac_re = re.compile('((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
    stations = list()
    for line in out.splitlines():
      sta = stamac_re.search(line)
      if sta is not None:
        stations.append(sta.group(1))
    return stations

  def GetAssociatedDevice(self, mac):
    """Return information about as associated STA.

    Args:
      mac: MAC address of the requested STA as a string, xx:xx:xx:xx:xx:xx

    Returns:
      An AssociatedDevice namedtuple.
    """
    ad = collections.namedtuple(
        'AssociatedDevice', ('AssociatedDeviceMACAddress '
                             'AssociatedDeviceAuthenticationState '
                             'LastDataTransmitRate'))
    ad.AssociatedDeviceMACAddress = mac
    ad.AssociatedDeviceAuthenticationState = False
    ad.LastDataTransmitRate = '0'
    out = self._SubprocessWithOutput(['sta_info', mac.upper()])
    tx_re = re.compile('rate of last tx pkt: (\d+) kbps')
    for line in out.splitlines():
      if line.find('AUTHENTICATED') >= 0:
        ad.AssociatedDeviceAuthenticationState = True
      tx_rate = tx_re.search(line)
      if tx_rate is not None:
        try:
          mbps = int(tx_rate.group(1)) / 1000
        except ValueError:
          mbps = 0
        ad.LastDataTransmitRate = str(mbps)
    return ad

  def GetAutoRateFallBackEnabled(self):
    """Return WLANConfiguration.AutoRateFallBackEnabled as a boolean."""
    out = self._SubprocessWithOutput(['interference'])
    mode_re = re.compile('\(mode (\d)\)')
    result = mode_re.search(out)
    mode = -1
    if result is not None:
      mode = int(result.group(1))
    return True if mode == 3 or mode == 4 else False

  def SetAutoRateFallBackEnabled(self, value):
    """Set WLANConfiguration.AutoRateFallBackEnabled, expects a boolean."""
    interference = 4 if value else 3
    self._SubprocessCall(['interference', str(interference)])

  def GetBasicDataTransmitRates(self):
    out = self._SubprocessWithOutput(['rateset'])
    basic_re = re.compile('([0123456789]+(?:\.[0123456789]+)?)\(b\)')
    return ','.join(basic_re.findall(out))

  def GetBSSID(self):
    out = self._SubprocessWithOutput(['bssid'])
    bssid_re = re.compile('((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
    for line in out.splitlines():
      bssid = bssid_re.match(line)
      if bssid is not None:
        return bssid.group(1)
    return '00:00:00:00:00:00'

  def SetBSSID(self, value):
    self._SubprocessCall(['bssid', value])

  def ValidateBSSID(self, value):
    lower = value.lower()
    if lower == '00:00:00:00:00:00' or lower == 'ff:ff:ff:ff:ff:ff':
      return False
    bssid_re = re.compile('((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
    if bssid_re.search(value) is None:
      return False
    return True

  def GetBssStatus(self):
    out = self._SubprocessWithOutput(['bss'])
    lower = out.strip().lower()
    if lower == 'up':
      return 'Up'
    elif lower == 'down':
      return 'Disabled'
    else:
      return 'Error'

  def SetBssStatus(self, enable):
    status = 'up' if enable else 'down'
    self._SubprocessCall(['bss', status])

  def GetChannel(self):
    out = self._SubprocessWithOutput(['channel'])
    chan_re = re.compile('current mac channel(?:\s+)(\d+)')
    for line in out.splitlines():
      mr = chan_re.match(line)
      if mr is not None:
        return int(mr.group(1))
    return 0

  def SetChannel(self, value):
    self._SubprocessCall(['channel', value])

  def ValidateChannel(self, value):
    if not IsInteger(value):
      return False
    iv = int(value)
    if iv in range(1, 14):
      return True  # 2.4 GHz. US allows 1-11, Japan allows 1-13.
    if iv in range(36, 144, 4):
      return True  # 5 GHz lower bands
    if iv in range(149, 169, 4):
      return True  # 5 GHz upper bands
    return False

  def EM_StringToBitmap(self, enum):
    wsec = {'X_CATAWAMPUS-ORG_None': EM_NONE,
            'None': EM_NONE,
            'WEPEncryption': EM_WEP,
            'TKIPEncryption': EM_TKIP,
            'WEPandTKIPEncryption': EM_WEP | EM_TKIP,
            'AESEncryption': EM_AES,
            'WEPandAESEncryption': EM_WEP | EM_AES,
            'TKIPandAESEncryption': EM_TKIP | EM_AES,
            'WEPandTKIPandAESEncryption': EM_WEP | EM_TKIP | EM_AES}
    return wsec.get(enum, EM_NONE)

  def EM_BitmapToString(self, bitmap):
    bmap = {EM_NONE: 'X_CATAWAMPUS-ORG_None',
            EM_WEP: 'WEPEncryption',
            EM_TKIP: 'TKIPEncryption',
            EM_WEP | EM_TKIP: 'WEPandTKIPEncryption',
            EM_AES: 'AESEncryption',
            EM_WEP | EM_AES: 'WEPandAESEncryption',
            EM_TKIP | EM_AES: 'TKIPandAESEncryption',
            EM_WEP | EM_TKIP | EM_AES: 'WEPandTKIPandAESEncryption'}
    return bmap.get(bitmap)

  def GetEncryptionModes(self):
    out = self._SubprocessWithOutput(['wsec'])
    try:
      w = int(out.strip()) & 0x7
      return self.EM_BitmapToString(w)
    except ValueError:
      return 'X_CATAWAMPUS-ORG_None'

  def SetEncryptionModes(self, value):
    self._SubprocessCall(['wsec', str(value)])

  def ValidateEncryptionModes(self, value):
    ENCRYPTTYPES = frozenset(['X_CATAWAMPUS-ORG_None', 'None', 'WEPEncryption',
                              'TKIPEncryption', 'WEPandTKIPEncryption',
                              'AESEncryption', 'WEPandAESEncryption',
                              'TKIPandAESEncryption',
                              'WEPandTKIPandAESEncryption'])
    return True if value in ENCRYPTTYPES else False

  def SetJoin(self, ssid, amode):
    self._SubprocessCall(['join', str(ssid), 'imode', 'bss',
                          'amode', str(amode)])

  def GetOperationalDataTransmitRates(self):
    out = self._SubprocessWithOutput(['rateset'])
    oper_re = re.compile('([0123456789]+(?:\.[0123456789]+)?)')
    if out:
      line1 = out.splitlines()[0]
    else:
      line1 = ''
    return ','.join(oper_re.findall(line1))

  def SetPMK(self, value):
    self._SubprocessCall(['set_pmk', value])

  def GetPossibleChannels(self):
    out = self._SubprocessWithOutput(['channels'])
    if out:
      channels = [int(x) for x in out.split()]
      return wifi.ContiguousRanges(channels)
    else:
      return ''

  def GetRadioEnabled(self):
    out = self._SubprocessWithOutput(['radio'])
    # This may look backwards, but I assure you it is correct. If the
    # radio is off, 'wl radio' returns 0x0001.
    try:
      return False if int(out.strip(), 0) == 1 else True
    except ValueError:
      return False

  def SetRadioEnabled(self, value):
    radio = 'on' if value else 'off'
    self._SubprocessCall(['radio', radio])

  def GetRegulatoryDomain(self):
    out = self._SubprocessWithOutput(['country'])
    fields = out.split()
    if fields:
      return fields[0]
    else:
      return ''

  def SetRegulatoryDomain(self, value):
    self._SubprocessCall(['country', value])

  def ValidateRegulatoryDomain(self, value):
    out = self._SubprocessWithOutput(['country', 'list'])
    countries = set()
    for line in out.splitlines():
      fields = line.split(' ')
      if len(fields) and len(fields[0]) == 2:
        countries.add(fields[0])
    return True if value in countries else False

  def SetReset(self, do_reset):
    status = 'down' if do_reset else 'up'
    self._SubprocessCall([status])

  def GetSSID(self):
    """Return current Wifi SSID."""
    out = self._SubprocessWithOutput(['ssid'])
    ssid_re = re.compile('Current SSID: "(.*)"')
    for line in out.splitlines():
      ssid = ssid_re.match(line)
      if ssid is not None:
        return ssid.group(1)
    return ''

  def SetSSID(self, value, cfgnum=None):
    self._SubprocessCall(['up'])
    if cfgnum is not None:
      self._SubprocessCall(['ssid', '-C', str(cfgnum), value])
    else:
      self._SubprocessCall(['ssid', value])

  def ValidateSSID(self, value):
    if len(value) > 32:
      return False
    return True

  def GetSSIDAdvertisementEnabled(self):
    out = self._SubprocessWithOutput(['closed'])
    return True if out.strip() == '0' else False

  def SetSSIDAdvertisementEnabled(self, value):
    closed = '0' if value else '1'
    self._SubprocessCall(['closed', closed])

  def SetSupWpa(self, value):
    sup_wpa = '1' if value else '0'
    self._SubprocessCall(['sup_wpa', sup_wpa])

  def GetTransmitPower(self):
    out = self._SubprocessWithOutput(['pwr_percent'])
    return out.strip()

  def SetTransmitPower(self, value):
    self._SubprocessCall(['pwr_percent', value])

  def ValidateTransmitPower(self, value):
    if not IsInteger(value):
      return False
    percent = int(value)
    if percent < 0 or percent > 100:
      return False
    return True

  def GetTransmitPowerSupported(self):
    # tr-98 describes this as a comma separated list, limited to string(64)
    # clearly it is expected to be a small number of discrete steps.
    # This chipset appears to have no such restriction. Hope a range is ok.
    return '1-100'

  def SetWepKey(self, index, key, mac=None):
    wl_cmd = ['addwep', str(index), key]
    if mac is not None:
      wl_cmd.append(str(mac))
    self._SubprocessCall(wl_cmd)

  def ClrWepKey(self, index):
    self._SubprocessCall(['rmwep', str(index)])

  def SetWepKeyIndex(self, index):
    # We do not use check_call here because primary_key fails if no WEP
    # keys have been configured, but we keep the code simple to always set it.
    subprocess.call([WL_EXE, '-i', self._if, 'primary_key', str(index)])

  def SetWepStatus(self, enable):
    status = 'on' if enable else 'off'
    self._SubprocessCall(['wepstatus', status])

  def GetWpaAuth(self):
    return self._SubprocessWithOutput(['wpa_auth'])

  def SetWpaAuth(self, value):
    self._SubprocessCall(['wpa_auth', str(value)])


class BrcmWifiWlanConfiguration(BASE98WIFI):
  """An implementation of tr98 WLANConfiguration for Broadcom Wifi chipsets."""

  def __init__(self, ifname):
    BASE98WIFI.__init__(self)
    self._ifname = ifname
    self.wl = Wl(ifname)

    # Unimplemented, but not yet evaluated
    self.Unexport('Alias')
    self.Unexport('BeaconAdvertisementEnabled')
    self.Unexport('ChannelsInUse')
    self.Unexport('MaxBitRate')
    self.Unexport('PossibleDataTransmitRates')
    self.Unexport('TotalIntegrityFailures')
    self.Unexport('TotalPSKFailures')

    self.AssociatedDeviceList = tr.core.AutoDict(
        'AssociatedDeviceList', iteritems=self.IterAssociations,
        getitem=self.GetAssociationByIndex)

    self.PreSharedKeyList = {}
    for i in range(1, 2):
      # tr-98 spec deviation: spec says 10 PreSharedKeys objects,
      # BRCM only supports one.
      self.PreSharedKeyList[i] = wifi.PreSharedKey98()

    self.WEPKeyList = {}
    for i in range(1, 5):
      self.WEPKeyList[i] = wifi.WEPKey98()

    self.LocationDescription = ''

    # No RADIUS support, could be added later.
    self.Unexport('AuthenticationServiceMode')

    # Local settings, currently unimplemented. Will require more
    # coordination with the underlying platform support.
    self.Unexport('InsecureOOBAccessEnabled')

    # MAC Access controls, currently unimplemented but could be supported.
    self.Unexport('MACAddressControlEnabled')

    # Wifi Protected Setup, currently unimplemented and not recommended.
    self.Unexport(objects='WPS')

    # Wifi MultiMedia, currently unimplemented but could be supported.
    # "wl wme_*" commands
    self.Unexport(lists='APWMMParameter')
    self.Unexport(lists='STAWMMParameter')
    self.Unexport('UAPSDEnable')
    self.Unexport('WMMEnable')

    # WDS, currently unimplemented but could be supported at some point.
    self.Unexport('PeerBSSID')
    self.Unexport('DistanceFromRoot')

    self.config = self._GetDefaultSettings()
    self.old_config = None

  def _GetDefaultSettings(self):
    obj = WifiConfig()
    obj.p_auto_channel_enable = True
    obj.p_auto_rate_fallback_enabled = None
    obj.p_basic_authentication_mode = 'None'
    obj.p_basic_encryption_modes = 'WEPEncryption'
    obj.p_beacon_type = 'WPAand11i'
    obj.p_bssid = None
    obj.p_channel = None
    obj.p_enable = False
    obj.p_ieee11i_authentication_mode = 'PSKAuthentication'
    obj.p_ieee11i_encryption_modes = 'X_CATAWAMPUS-ORG_None'
    obj.p_radio_enabled = True
    obj.p_regulatory_domain = None
    obj.p_ssid = None
    obj.p_ssid_advertisement_enabled = None
    obj.p_transmit_power = None
    obj.p_wepkeyindex = 1
    obj.p_wpa_authentication_mode = 'PSKAuthentication'
    obj.p_wpa_encryption_modes = 'X_CATAWAMPUS-ORG_None'
    return obj

  def StartTransaction(self):
    config = self.config
    self.config = copy.copy(config)
    self.old_config = config

  def AbandonTransaction(self):
    self.config = self.old_config
    self.old_config = None

  def CommitTransaction(self):
    self.old_config = None
    self._ConfigureBrcmWifi()

  @property
  def Name(self):
    return self._ifname

  @property  # TODO(dgentry) need @sessioncache decorator.
  def Stats(self):
    return BrcmWlanConfigurationStats(self._ifname)

  @property
  def Standard(self):
    return 'n'

  @property
  def DeviceOperationMode(self):
    return 'InfrastructureAccessPoint'

  @property
  def UAPSDSupported(self):
    return False

  @property
  def WEPEncryptionLevel(self):
    return 'Disabled,40-bit,104-bit'

  @property
  def WMMSupported(self):
    return False

  @property
  def TotalAssociations(self):
    return len(self.AssociatedDeviceList)

  def GetAutoRateFallBackEnabled(self):
    return self.wl.GetAutoRateFallBackEnabled()

  def SetAutoRateFallBackEnabled(self, value):
    self.config.p_auto_rate_fallback_enabled = tr.cwmpbool.parse(value)

  AutoRateFallBackEnabled = property(
      GetAutoRateFallBackEnabled, SetAutoRateFallBackEnabled, None,
      'WLANConfiguration.AutoRateFallBackEnabled')

  def GetBasicAuthenticationMode(self):
    return self.config.p_basic_authentication_mode

  def SetBasicAuthenticationMode(self, value):
    if not value in BASICAUTHMODES:
      raise ValueError('Unsupported BasicAuthenticationMode %s' % value)
    self.config.p_basic_authentication_mode = value

  BasicAuthenticationMode = property(
      GetBasicAuthenticationMode, SetBasicAuthenticationMode, None,
      'WLANConfiguration.BasicAuthenticationMode')

  def GetBasicDataTransmitRates(self):
    return self.wl.GetBasicDataTransmitRates()

  # TODO(dgentry) implement SetBasicDataTransmitRates

  BasicDataTransmitRates = property(
      GetBasicDataTransmitRates, None, None,
      'WLANConfiguration.BasicDataTransmitRates')

  def GetBasicEncryptionModes(self):
    return self.config.p_basic_encryption_modes

  def SetBasicEncryptionModes(self, value):
    if value not in BASICENCRYPTIONS:
      raise ValueError('Unsupported BasicEncryptionMode: %s' % value)
    self.config.p_basic_encryption_modes = value

  BasicEncryptionModes = property(GetBasicEncryptionModes,
                                  SetBasicEncryptionModes, None,
                                  'WLANConfiguration.BasicEncryptionModes')

  def GetBeaconType(self):
    return self.config.p_beacon_type

  def SetBeaconType(self, value):
    if value not in BEACONS:
      raise ValueError('Unsupported BeaconType: %s' % value)
    self.config.p_beacon_type = value

  BeaconType = property(GetBeaconType, SetBeaconType, None,
                        'WLANConfiguration.BeaconType')

  def GetBSSID(self):
    return self.wl.GetBSSID()

  def SetBSSID(self, value):
    if not self.wl.ValidateBSSID(value):
      raise ValueError('Invalid BSSID: %s' % value)
    self.config.p_bssid = value

  BSSID = property(GetBSSID, SetBSSID, None, 'WLANConfiguration.BSSID')

  def GetChannel(self):
    return self.wl.GetChannel()

  def SetChannel(self, value):
    if not self.wl.ValidateChannel(value):
      raise ValueError('Invalid Channel: %s' % value)
    self.config.p_channel = value
    self.config.p_auto_channel_enable = False

  Channel = property(GetChannel, SetChannel, None, 'WLANConfiguration.Channel')

  def GetEnable(self):
    return self.config.p_enable

  def SetEnable(self, value):
    self.config.p_enable = tr.cwmpbool.parse(value)

  Enable = property(GetEnable, SetEnable, None, 'WLANConfiguration.Enable')

  def GetIEEE11iAuthenticationMode(self):
    auth = self.wl.GetWpaAuth().split()
    eap = True if 'WPA2-802.1x' in auth else False
    psk = True if 'WPA2-PSK' in auth else False
    if eap and psk:
      return 'EAPandPSKAuthentication'
    elif eap:
      return 'EAPAuthentication'
    else:
      return 'PSKAuthentication'

  def SetIEEE11iAuthenticationMode(self, value):
    if not value in WPAAUTHMODES:
      raise ValueError('Unsupported IEEE11iAuthenticationMode %s' % value)
    self.config.p_ieee11i_authentication_mode = value

  IEEE11iAuthenticationMode = property(
      GetIEEE11iAuthenticationMode, SetIEEE11iAuthenticationMode,
      None, 'WLANConfiguration.IEEE11iAuthenticationMode')

  def GetIEEE11iEncryptionModes(self):
    return self.wl.GetEncryptionModes()

  def SetIEEE11iEncryptionModes(self, value):
    if not self.wl.ValidateEncryptionModes(value):
      raise ValueError('Invalid IEEE11iEncryptionMode: %s' % value)
    self.config.p_ieee11i_encryption_modes = value

  IEEE11iEncryptionModes = property(
      GetIEEE11iEncryptionModes, SetIEEE11iEncryptionModes, None,
      'WLANConfiguration.IEEE11iEncryptionModes')

  def GetKeyPassphrase(self):
    psk = self.PreSharedKeyList[1]
    return psk.KeyPassphrase

  def SetKeyPassphrase(self, value):
    psk = self.PreSharedKeyList[1]
    psk.KeyPassphrase = value
    # TODO(dgentry) need to set WEPKeys, but this is fraught with peril.
    # If KeyPassphrase is not exactly 5 or 13 bytes it must be padded.
    # Apple uses different padding than Windows (and others).
    # http://support.apple.com/kb/HT1344

  KeyPassphrase = property(GetKeyPassphrase, SetKeyPassphrase, None,
                           'WLANConfiguration.KeyPassphrase')

  def GetOperationalDataTransmitRates(self):
    return self.wl.GetOperationalDataTransmitRates()

  # TODO(dgentry) - need to implement SetOperationalDataTransmitRates

  OperationalDataTransmitRates = property(
      GetOperationalDataTransmitRates, None,
      None, 'WLANConfiguration.OperationalDataTransmitRates')

  def GetPossibleChannels(self):
    return self.wl.GetPossibleChannels()

  PossibleChannels = property(GetPossibleChannels, None, None,
                              'WLANConfiguration.PossibleChannels')

  def GetRadioEnabled(self):
    return self.wl.GetRadioEnabled()

  def SetRadioEnabled(self, value):
    self.config.p_radio_enabled = tr.cwmpbool.parse(value)

  RadioEnabled = property(GetRadioEnabled, SetRadioEnabled, None,
                          'WLANConfiguration.RadioEnabled')

  def GetRegulatoryDomain(self):
    return self.wl.GetRegulatoryDomain()

  def SetRegulatoryDomain(self, value):
    if not self.wl.ValidateRegulatoryDomain(value):
      raise ValueError('Unknown RegulatoryDomain: %s' % value)
    self.config.p_regulatory_domain = value

  RegulatoryDomain = property(GetRegulatoryDomain, SetRegulatoryDomain, None,
                              'WLANConfiguration.RegulatoryDomain')

  def GetAutoChannelEnable(self):
    return self.config.p_auto_channel_enable

  def SetAutoChannelEnable(self, value):
    self.config.p_auto_channel_enable = tr.cwmpbool.parse(value)

  AutoChannelEnable = property(GetAutoChannelEnable, SetAutoChannelEnable,
                               None, 'WLANConfiguration.AutoChannelEnable')

  def GetSSID(self):
    return self.wl.GetSSID()

  def SetSSID(self, value):
    if not self.wl.ValidateSSID(value):
      raise ValueError('Invalid SSID: %s' % value)
    self.config.p_ssid = value

  SSID = property(GetSSID, SetSSID, None, 'WLANConfiguration.SSID')

  def GetSSIDAdvertisementEnabled(self):
    return self.wl.GetSSIDAdvertisementEnabled()

  def SetSSIDAdvertisementEnabled(self, value):
    self.config.p_ssid_advertisement_enabled = tr.cwmpbool.parse(value)

  SSIDAdvertisementEnabled = property(
      GetSSIDAdvertisementEnabled, SetSSIDAdvertisementEnabled, None,
      'WLANConfiguration.SSIDAdvertisementEnabled')

  def GetBssStatus(self):
    return self.wl.GetBssStatus()

  Status = property(GetBssStatus, None, None, 'WLANConfiguration.Status')

  def GetTransmitPower(self):
    return self.wl.GetTransmitPower()

  def SetTransmitPower(self, value):
    if not self.wl.ValidateTransmitPower(value):
      raise ValueError('Invalid TransmitPower: %s' % value)
    self.config.p_transmit_power = value

  TransmitPower = property(GetTransmitPower, SetTransmitPower, None,
                           'WLANConfiguration.TransmitPower')

  def GetTransmitPowerSupported(self):
    return self.wl.GetTransmitPowerSupported()

  TransmitPowerSupported = property(GetTransmitPowerSupported, None, None,
                                    'WLANConfiguration.TransmitPowerSupported')

  def GetWEPKeyIndex(self):
    return self.config.p_wepkeyindex

  def SetWEPKeyIndex(self, value):
    self.config.p_wepkeyindex = int(value)

  WEPKeyIndex = property(GetWEPKeyIndex, SetWEPKeyIndex, None,
                         'WLANConfiguration.WEPKeyIndex')

  def GetWPAAuthenticationMode(self):
    auth = self.wl.GetWpaAuth().split()
    psk = True if 'WPA-PSK' in auth else False
    eap = True if 'WPA-802.1x' in auth else False
    if eap:
      return 'EAPAuthentication'
    else:
      return 'PSKAuthentication'

  def SetWPAAuthenticationMode(self, value):
    if not value in WPAAUTHMODES:
      raise ValueError('Unsupported WPAAuthenticationMode %s' % value)
    self.config.p_wpa_authentication_mode = value

  WPAAuthenticationMode = property(
      GetWPAAuthenticationMode, SetWPAAuthenticationMode,
      None, 'WLANConfiguration.WPAAuthenticationMode')

  def GetEncryptionModes(self):
    return self.wl.GetEncryptionModes()

  def SetWPAEncryptionModes(self, value):
    if not self.wl.ValidateEncryptionModes(value):
      raise ValueError('Invalid WPAEncryptionMode: %s' % value)
    self.config.p_wpa_encryption_modes = value

  WPAEncryptionModes = property(GetEncryptionModes, SetWPAEncryptionModes, None,
                                'WLANConfiguration.WPAEncryptionModes')

  def _ConfigureBrcmWifi(self):
    """Issue commands to the wifi device to configure it.

    The Wifi driver is somewhat picky about the order of the commands.
    For example, some settings can only be changed while the radio is on.
    Make sure any changes made in this routine work in a real system, unit
    tests do not (and realistically, cannot) model all behaviors of the
    real wl utility.
    """

    if not self.config.p_enable or not self.config.p_radio_enabled:
      self.wl.SetRadioEnabled(False)
      return

    self.wl.SetRadioEnabled(True)
    self.wl.SetApMode()
    if self.config.p_auto_channel_enable:
      self.wl.DoAutoChannelSelect()
    self.wl.SetBssStatus(False)
    if self.config.p_auto_rate_fallback_enabled is not None:
      self.wl.SetAutoRateFallBackEnabled(
          self.config.p_auto_rate_fallback_enabled)
    if self.config.p_bssid is not None:
      self.wl.SetBSSID(self.config.p_bssid)
    if self.config.p_channel is not None:
      self.wl.SetChannel(self.config.p_channel)
    if self.config.p_regulatory_domain is not None:
      self.wl.SetRegulatoryDomain(self.config.p_regulatory_domain)
    if self.config.p_ssid_advertisement_enabled is not None:
      self.wl.SetSSIDAdvertisementEnabled(
          self.config.p_ssid_advertisement_enabled)
    if self.config.p_transmit_power is not None:
      self.wl.SetTransmitPower(self.config.p_transmit_power)

    # sup_wpa should only be set WPA/WPA2 modes, not for Basic.
    sup_wpa = False
    amode = 0
    if self.config.p_beacon_type.find('11i') >= 0:
      crypto = self.wl.EM_StringToBitmap(self.config.p_ieee11i_encryption_modes)
      if crypto != EM_NONE:
        amode = 128
      sup_wpa = True
    elif self.config.p_beacon_type.find('WPA') >= 0:
      crypto = self.wl.EM_StringToBitmap(self.config.p_wpa_encryption_modes)
      if crypto != EM_NONE:
        amode = 4
      sup_wpa = True
    elif self.config.p_beacon_type.find('Basic') >= 0:
      crypto = self.wl.EM_StringToBitmap(self.config.p_basic_encryption_modes)
    else:
      crypto = EM_NONE
    self.wl.SetEncryptionModes(crypto)
    self.wl.SetSupWpa(sup_wpa)
    self.wl.SetWpaAuth(amode)

    for idx, psk in self.PreSharedKeyList.items():
      key = psk.GetKey(self.config.p_ssid)
      if key:
        self.wl.SetPMK(key)

    if self.config.p_ssid is not None:
      time.sleep(WL_SLEEP)
      self.wl.SetSSID(self.config.p_ssid)

    # Setting WEP key has to come after setting SSID. (Doesn't make sense
    # to me, it just doesn't work if you do it before setting SSID.)
    for idx, wep in self.WEPKeyList.items():
      key = wep.WEPKey
      if key is None:
        self.wl.ClrWepKey(idx-1)
      else:
        self.wl.SetWepKey(idx-1, key)
    self.wl.SetWepKeyIndex(self.config.p_wepkeyindex)

  def GetTotalBytesReceived(self):
    # TODO(dgentry) cache for lifetime of session
    counters = self.wl.GetWlCounters()
    return int(counters.get('rxbyte', 0))

  TotalBytesReceived = property(GetTotalBytesReceived, None, None,
                                'WLANConfiguration.TotalBytesReceived')

  def GetTotalBytesSent(self):
    counters = self.wl.GetWlCounters()
    return int(counters.get('txbyte', 0))

  TotalBytesSent = property(GetTotalBytesSent, None, None,
                            'WLANConfiguration.TotalBytesSent')

  def GetTotalPacketsReceived(self):
    counters = self.wl.GetWlCounters()
    return int(counters.get('rxframe', 0))

  TotalPacketsReceived = property(GetTotalPacketsReceived, None, None,
                                  'WLANConfiguration.TotalPacketsReceived')

  def GetTotalPacketsSent(self):
    counters = self.wl.GetWlCounters()
    return int(counters.get('txframe', 0))

  TotalPacketsSent = property(GetTotalPacketsSent, None, None,
                              'WLANConfiguration.TotalPacketsSent')

  def GetAssociation(self, mac):
    """Get an AssociatedDevice object for the given STA."""
    ad = BrcmWlanAssociatedDevice(self.wl.GetAssociatedDevice(mac))
    if ad:
      ad.ValidateExports()
    return ad

  def IterAssociations(self):
    """Retrieves a list of all associated STAs."""
    stations = self.wl.GetAssociatedDevices()
    for idx, mac in enumerate(stations):
      yield idx, self.GetAssociation(mac)

  def GetAssociationByIndex(self, index):
    stations = self.wl.GetAssociatedDevices()
    return self.GetAssociation(stations[index])


class BrcmWlanConfigurationStats(netdev.NetdevStatsLinux26, BASE98WIFI.Stats):
  """tr98 InternetGatewayDevice.LANDevice.WLANConfiguration.Stats."""

  def __init__(self, ifname):
    netdev.NetdevStatsLinux26.__init__(self, ifname)
    BASE98WIFI.Stats.__init__(self)


class BrcmWlanAssociatedDevice(BASE98WIFI.AssociatedDevice):
  """Implementation of tr98 AssociatedDevice for Broadcom Wifi chipsets."""

  def __init__(self, device):
    BASE98WIFI.AssociatedDevice.__init__(self)
    self._device = device
    self.Unexport('AssociatedDeviceIPAddress')
    self.Unexport('LastPMKId')
    self.Unexport('LastRequestedUnicastCipher')
    self.Unexport('LastRequestedMulticastCipher')

  def __getattr__(self, name):
    if hasattr(self._device, name):
      return getattr(self._device, name)
    else:
      raise AttributeError


def main():
  print tr.core.DumpSchema(BrcmWifiWlanConfiguration)

if __name__ == '__main__':
  main()
