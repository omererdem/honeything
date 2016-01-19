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

"""Unit tests for wifi.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest

import google3
import wifi


class WifiTest(unittest.TestCase):
  def testContiguousRanges(self):
    self.assertEqual(wifi.ContiguousRanges([1, 2, 3, 4, 5]), '1-5')
    self.assertEqual(wifi.ContiguousRanges([1, 2, 3, 5]), '1-3,5')
    self.assertEqual(wifi.ContiguousRanges([1, 2, 3, 5, 6, 7]), '1-3,5-7')
    self.assertEqual(wifi.ContiguousRanges([1, 2, 3, 5, 7, 8, 9]), '1-3,5,7-9')
    self.assertEqual(wifi.ContiguousRanges([1, 3, 5, 7, 9]), '1,3,5,7,9')

  def testPreSharedKeyValidate(self):
    psk = wifi.PreSharedKey98()
    psk.ValidateExports()

  def testPBKDF2(self):
    psk = wifi.PreSharedKey98()
    # http://connect.microsoft.com/VisualStudio/feedback/details/95506/
    psk.KeyPassphrase = 'ThisIsAPassword'
    key = psk.GetKey('ThisIsASSID')
    self.assertEqual(
        key, '0dc0d6eb90555ed6419756b9a15ec3e3209b63df707dd508d14581f8982721af')

  def testWEPKeyValidate(self):
    wk = wifi.WEPKey98()
    wk.ValidateExports()


if __name__ == '__main__':
  unittest.main()
