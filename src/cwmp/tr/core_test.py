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
"""Tests for core.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import unittest
import core


class TestObject(core.Exporter):
  def __init__(self):
    core.Exporter.__init__(self)
    self.Export(params=['TestParam'],
                objects=['SubObj'],
                lists=['Counter'])
    self.TestParam = 5
    self.SubObj = TestObject.SubObj()
    self.CounterList = {}
    self.Counter = TestObject.SubObj

  class SubObj(core.Exporter):
    gcount = [0]

    def __init__(self):
      core.Exporter.__init__(self)
      self.Export(params=['Count'])

      self.gcount[0] += 1
      self.Count = self.gcount[0]


class CoreTest(unittest.TestCase):
  def setUp(self):
    # Reset the global gcount
    TestObject.SubObj.gcount = [0]

  def testCore(self):
    o = TestObject()
    self.assertTrue(o)
    o.ValidateExports()
    o.AddExportObject('Counter')
    o.AddExportObject('Counter')
    o.AddExportObject('Counter')
    print o.ListExports(recursive=False)
    print o.ListExports(recursive=True)
    self.assertEqual(list(o.ListExports()),
                     ['Counter.', 'SubObj.', 'TestParam'])
    self.assertEqual(list(o.ListExports(recursive=True)),
                     ['Counter.',
                      'Counter.0.', 'Counter.0.Count',
                      'Counter.1.', 'Counter.1.Count',
                      'Counter.2.', 'Counter.2.Count',
                      'SubObj.', 'SubObj.Count', 'TestParam'])

    ds1 = core.DumpSchema(TestObject)
    ds2 = core.DumpSchema(o)
    self.assertEqual(ds1, ds2)

    o.DeleteExportObject('Counter', 1)
    self.assertEqual(list(o.ListExports(recursive=True)),
                     ['Counter.',
                      'Counter.0.', 'Counter.0.Count',
                      'Counter.2.', 'Counter.2.Count',
                      'SubObj.', 'SubObj.Count', 'TestParam'])
    self.assertEqual([(idx, i.Count) for idx, i in o.CounterList.items()],
                     [(0, 2), (2, 4)])
    idx, eo = o.AddExportObject('Counter', 'fred')
    eo.Count = 99
    print o.ListExports(recursive=True)
    self.assertEqual([(idx, i.Count) for idx, i in o.CounterList.items()],
                     [(0, 2), (2, 4), ('fred', 99)])
    print core.Dump(o)
    o.ValidateExports()

  def testCanonicalName(self):
    o = TestObject()
    self.assertTrue(o)
    o.ValidateExports()
    name = o.GetCanonicalName(o.SubObj)
    self.assertEqual('SubObj', name)

    (idx1, obj1) = o.AddExportObject('Counter')
    (idx2, obj2) = o.AddExportObject('Counter')
    (idx3, obj3) = o.AddExportObject('Counter')
    name = o.GetCanonicalName(obj3)
    self.assertEqual('Counter.2', name)



if __name__ == '__main__':
  unittest.main()
