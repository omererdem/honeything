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

# TR-069 has mandatory attribute names that don't comply with policy
#pylint: disable-msg=C6409
#
"""Tests for persist.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import os
import tempfile
import unittest

import google3
import core
import persist


class Leaf(core.Exporter):
  def __init__(self, n):
    core.Exporter.__init__(self, defaults=dict(Number=n))
    self.Export(params=['Number'])


class Tree(Leaf):
  def __init__(self, n=0, subtree=None):
    Leaf.__init__(self, n)
    if not subtree:
      subtree = Leaf(0)
    self.Export(objects=['Tree'], lists=['Sub'])
    self.Tree = subtree
    self.SubList = {}

Tree.Sub = Tree


class PersistTest(unittest.TestCase):
  def testPersist(self):
    fd, dbname = tempfile.mkstemp()
    os.close(fd)
    print 'database file: %s' % dbname

    t = Tree(5, Leaf(6))
    t.SubList[7] = Tree(77, Tree(777, Leaf(7777)))
    t.SubList[11] = Tree(88, Tree(888, Leaf(8888)))
    t.SubList[11].SubList[9] = Tree(99, Leaf(9999))
    print core.Dump(t)
    p = persist.Store(dbname, t)
    p.Save()

    t2 = Tree(0, Leaf(0))
    p2 = persist.Store(dbname, t2)
    p2.Load()
    print core.Dump(t2)

    self.assertEqual(t.Number, 5)
    self.assertEqual(t2.Number, 5)
    self.assertEqual(t.SubList[11].SubList[9].Tree.Number, 9999)
    self.assertEqual(t2.SubList[11].SubList[9].Tree.Number, 9999)
    self.assertEqual(t.SubList[11].Tree.Tree.Number, 8888)
    self.assertRaises(AttributeError, lambda: t2.SubList[11].Tree.Tree.Number)
    self.assertRaises(KeyError, lambda: t2.SubList[12].Tree.Tree.Number)


if __name__ == '__main__':
  unittest.main()
