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

"""Unit tests for gmoca.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import base64
import bz2
import tempfile
import unittest

import google3
import gmoca


class GMoCATest(unittest.TestCase):
  """Tests for gmoca.py."""

  def testValidateExports(self):
    gmoca.MOCACTL = 'testdata/device/mocactl'
    gm = gmoca.GMoCA()
    gm.ValidateExports()

  def testDebugOutput(self):
    gmoca.MOCACTL = 'testdata/device/mocactl'
    gm = gmoca.GMoCA()
    out = gm.DebugOutput
    self.assertTrue(len(out) > 1024)
    decode = base64.b64decode(out)  # will raise TypeError if invalid
    decomp = bz2.decompress(decode)
    self.assertTrue(len(decomp) > 1024)
    self.assertTrue(decomp.find('X_GOOGLE-COM_GMOCA') >= 0)


if __name__ == '__main__':
  unittest.main()
