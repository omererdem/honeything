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

"""Implementations of platform-independant tr-98/181 WLAN objects."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import pbkdf2
import tr.tr098_v1_4


def ContiguousRanges(seq):
  """Given an integer sequence, return contiguous ranges.

  This is expected to be useful for the tr-98 WLANConfig PossibleChannels
  parameter.

  Args:
    seq: a sequence of integers, like [1,2,3,4,5]

  Returns:
    A string of the collapsed ranges.
    Given [1,2,3,4,5] as input, will return '1-5'
  """
  in_range = False
  prev = seq[0]
  output = list(str(seq[0]))
  for item in seq[1:]:
    if item == prev + 1:
      if not in_range:
        in_range = True
        output.append('-')
    else:
      if in_range:
        output.append(str(prev))
      output.append(',' + str(item))
      in_range = False
    prev = item
  if in_range:
    output.append(str(prev))
  return ''.join(output)


class PreSharedKey98(tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice.LANDevice.WLANConfiguration.PreSharedKey):
  """InternetGatewayDevice.WLANConfiguration.{i}.PreSharedKey.{i}."""

  def __init__(self):
    super(PreSharedKey98, self).__init__()
    self.Unexport('Alias')
    self.key = None
    self.passphrase = None
    self.key_pbkdf2 = None
    self.salt = None
    self.AssociatedDeviceMACAddress = None

  def GetKey(self, salt):
    """Return the key to program into the Wifi chipset.

    Args:
      salt: Per WPA2 spec, the SSID is used as the salt.
    Returns:
      The key as a hex string, or None if no key.
    """
    if self.key is not None:
      return self.key
    if self.key_pbkdf2 is None or salt != self.salt:
      self.salt = salt
      self.key_pbkdf2 = self._GeneratePBKDF2(salt)
    if self.key_pbkdf2 is not None:
      return self.key_pbkdf2
    return None

  def _GeneratePBKDF2(self, salt):
    """Compute WPA2 key from a passphrase."""
    if self.passphrase is None:
      return None
    return pbkdf2.pbkdf2_hex(self.passphrase, salt=salt,
                             iterations=4096, keylen=32)

  def SetPreSharedKey(self, value):
    self.key = value
    self.key_pbkdf2 = None

  def GetPreSharedKey(self):
    return self.key

  PreSharedKey = property(
      GetPreSharedKey, SetPreSharedKey, None,
      'WLANConfiguration.{i}.PreSharedKey.{i}.PreSharedKey')

  def SetKeyPassphrase(self, value):
    self.passphrase = value
    self.key = None
    self.key_pbkdf2 = None

  def GetKeyPassphrase(self):
    return self.passphrase

  KeyPassphrase = property(
      GetKeyPassphrase, SetKeyPassphrase, None,
      'WLANConfiguration.{i}.PreSharedKey.{i}.KeyPassphrase')


class WEPKey98(tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice.LANDevice.WLANConfiguration.WEPKey):
  """InternetGatewayDevice.WLANConfiguration.{i}.WEPKey.{i}."""

  def __init__(self):
    super(WEPKey98, self).__init__()
    self.Unexport('Alias')
    self.WEPKey = None


def main():
  pass

if __name__ == '__main__':
  main()
