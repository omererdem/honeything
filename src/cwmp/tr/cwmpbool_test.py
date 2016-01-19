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

"""Unit tests for cwmpboolean.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest

import google3
import cwmpbool


class CwmpBoolTest(unittest.TestCase):
  """Tests for boolean formatting."""

  def testParse(self):
    self.assertTrue(cwmpbool.parse('true'))
    self.assertTrue(cwmpbool.parse('True'))
    self.assertTrue(cwmpbool.parse('1'))
    self.assertFalse(cwmpbool.parse('false'))
    self.assertFalse(cwmpbool.parse('False'))
    self.assertFalse(cwmpbool.parse('0'))
    self.assertRaises(ValueError, cwmpbool.parse, 'booga')

  def testFormat(self):
    self.assertEqual(cwmpbool.format(True), '1')
    self.assertEqual(cwmpbool.format(False), '0')

  def testValid(self):
    self.assertTrue(cwmpbool.valid('True'))
    self.assertTrue(cwmpbool.valid('true'))
    self.assertTrue(cwmpbool.valid('False'))
    self.assertTrue(cwmpbool.valid('false'))
    self.assertTrue(cwmpbool.valid('0'))
    self.assertTrue(cwmpbool.valid('1'))
    self.assertFalse(cwmpbool.valid(''))
    self.assertFalse(cwmpbool.valid('booga'))

if __name__ == '__main__':
  unittest.main()
