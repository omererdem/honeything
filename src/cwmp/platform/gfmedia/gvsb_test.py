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

"""Unit tests for gvsb.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import unittest

import google3
import gvsb


class GvsbTest(unittest.TestCase):
  """Tests for gvsb.py."""

  def testValidateExports(self):
    gv = gvsb.Gvsb()
    gv.ValidateExports()

  def testEpgPrimary(self):
    temp = tempfile.NamedTemporaryFile()
    gvsb.EPGPRIMARYFILE = temp.name
    gv = gvsb.Gvsb()
    gv.StartTransaction()
    gv.EpgPrimary = 'Booga'
    gv.CommitTransaction()
    self.assertEqual(gv.EpgPrimary, 'Booga')
    temp.seek(0)
    self.assertEqual(temp.readline(), 'Booga')
    temp.close()

  def testEpgSecondary(self):
    temp = tempfile.NamedTemporaryFile()
    gvsb.EPGSECONDARYFILE = temp.name
    gv = gvsb.Gvsb()
    gv.StartTransaction()
    gv.EpgSecondary = 'Booga'
    gv.CommitTransaction()
    self.assertEqual(gv.EpgSecondary, 'Booga')
    temp.seek(0)
    self.assertEqual(temp.readline(), 'Booga')
    temp.close()

  def testGvsbServer(self):
    temp = tempfile.NamedTemporaryFile()
    gvsb.GVSBSERVERFILE = temp.name
    gv = gvsb.Gvsb()
    gv.StartTransaction()
    gv.GvsbServer = 'Booga'
    gv.CommitTransaction()
    self.assertEqual(gv.GvsbServer, 'Booga')
    temp.seek(0)
    self.assertEqual(temp.readline(), 'Booga')
    temp.close()

  def testGvsbChannelLineup(self):
    temp = tempfile.NamedTemporaryFile()
    gvsb.GVSBCHANNELFILE = temp.name
    gv = gvsb.Gvsb()
    self.assertEqual(gv.GvsbChannelLineup, 0)
    gv.StartTransaction()
    gv.GvsbChannelLineup = 1000
    gv.CommitTransaction()
    self.assertEqual(gv.GvsbChannelLineup, 1000)
    temp.seek(0)
    self.assertEqual(temp.readline(), '1000')
    temp.close()

  def testGvsbKick(self):
    temp = tempfile.NamedTemporaryFile()
    gvsb.GVSBKICKFILE = temp.name
    gv = gvsb.Gvsb()
    gv.StartTransaction()
    gv.GvsbKick = 'kickme'
    gv.CommitTransaction()
    self.assertEqual(gv.GvsbKick, 'kickme')
    temp.seek(0)
    self.assertEqual(temp.readline(), 'kickme')
    temp.close()

  def _FileIsEmpty(self, filename):
    st = os.stat(filename)
    return True if st and st.st_size == 0 else False

  def testInitEmptyFiles(self):
    tmpdir = tempfile.mkdtemp()
    gvsb.EPGPRIMARYFILE = os.path.join(tmpdir, 'epgprimaryfile')
    gvsb.EPGSECONDARYFILE = os.path.join(tmpdir, 'epgsecondaryfile')
    gvsb.GVSBSERVERFILE = os.path.join(tmpdir, 'gvsbserverfile')
    gvsb.GVSBCHANNELFILE = os.path.join(tmpdir, 'gvsbchannelfile')
    gvsb.GVSBKICKFILE = os.path.join(tmpdir, 'gvsbkickfile')
    gv = gvsb.Gvsb()
    gv.StartTransaction()
    gv.CommitTransaction()
    self.assertTrue(self._FileIsEmpty(gvsb.EPGPRIMARYFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.EPGSECONDARYFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.GVSBSERVERFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.GVSBCHANNELFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.GVSBKICKFILE))
    shutil.rmtree(tmpdir)

  def testAbandonTransaction(self):
    tmpdir = tempfile.mkdtemp()
    gvsb.EPGPRIMARYFILE = os.path.join(tmpdir, 'epgprimaryfile')
    gvsb.EPGSECONDARYFILE = os.path.join(tmpdir, 'epgsecondaryfile')
    gvsb.GVSBSERVERFILE = os.path.join(tmpdir, 'gvsbserverfile')
    gvsb.GVSBCHANNELFILE = os.path.join(tmpdir, 'gvsbchannelfile')
    gvsb.GVSBKICKFILE = os.path.join(tmpdir, 'gvsbkickfile')
    gv = gvsb.Gvsb()
    gv.StartTransaction()
    gv.EpgPrimary = 'epgprimary'
    gv.EpgSecondary = 'epgsecondary'
    gv.GvsbServer = 'gvsbserver'
    gv.GvsbChannelLineup = '1001'
    gv.GvsbKick = 'gvsbkick'
    gv.AbandonTransaction()
    self.assertTrue(self._FileIsEmpty(gvsb.EPGPRIMARYFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.EPGSECONDARYFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.GVSBSERVERFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.GVSBCHANNELFILE))
    self.assertTrue(self._FileIsEmpty(gvsb.GVSBKICKFILE))
    shutil.rmtree(tmpdir)


if __name__ == '__main__':
  unittest.main()
