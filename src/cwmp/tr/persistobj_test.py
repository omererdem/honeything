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

"""Unit tests for persistobj.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import shutil
import tempfile
import unittest

import google3
import persistobj


class PersistentObjectTest(unittest.TestCase):
  """Tests for persistobj.py PersistentObject."""

  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()

  def tearDown(self):
    shutil.rmtree(self.tmpdir)

  def testPersistentObjectAttrs(self):
    kwargs = {'foo1': 'bar1', 'foo2': 'bar2', 'foo3': 3}
    tobj = persistobj.PersistentObject(self.tmpdir, 'TestObj', **kwargs)
    self.assertEqual(tobj.foo1, 'bar1')
    self.assertEqual(tobj.foo2, 'bar2')
    self.assertEqual(tobj.foo3, 3)

  def testReversibleEncoding(self):
    kwargs = dict(foo1='bar1', foo3=3)
    tobj = persistobj.PersistentObject(self.tmpdir, 'TestObj', **kwargs)
    encoded = tobj._ToJson()
    decoded = tobj._FromJson(encoded)
    self.assertEqual(sorted(kwargs.items()), sorted(decoded.items()))

  def testWriteToFile(self):
    kwargs = dict(foo1='bar1', foo3=3)
    tobj = persistobj.PersistentObject(self.tmpdir, 'TestObj', **kwargs)
    encoded = open(tobj.filename).read()
    decoded = tobj._FromJson(encoded)
    self.assertEqual(sorted(kwargs.items()), sorted(decoded.items()))

  def testReadFromFile(self):
    contents = '{"foo": "bar", "baz": 4}'
    with tempfile.NamedTemporaryFile(dir=self.tmpdir, delete=False) as f:
      f.write(contents)
      f.close()
      tobj = persistobj.PersistentObject(self.tmpdir, 'TestObj',
                                         filename=f.name)
    self.assertEqual(tobj.foo, 'bar')
    self.assertEqual(tobj.baz, 4)

  def testReadFromCorruptFile(self):
    contents = 'this is not a JSON file'
    f = tempfile.NamedTemporaryFile(dir=self.tmpdir, delete=False)
    f.write(contents)
    f.close()
    self.assertRaises(ValueError, persistobj.PersistentObject,
                      self.tmpdir, 'TestObj', filename=f.name)

  def testUpdate(self):
    kwargs = dict(foo1='bar1', foo3=3)
    tobj = persistobj.PersistentObject(self.tmpdir, 'TestObj', **kwargs)
    tobj2 = persistobj.PersistentObject(self.tmpdir, 'TestObj',
                                        filename=tobj.filename)
    self.assertEqual(list(sorted(tobj.items())), list(sorted(tobj2.items())))
    kwargs['foo1'] = 'bar2'
    tobj.Update(**kwargs)
    tobj3 = persistobj.PersistentObject(self.tmpdir, 'TestObj',
                                        filename=tobj.filename)
    self.assertEqual(list(sorted(tobj.items())), list(sorted(tobj3.items())))

  def testUpdateInline(self):
    kwargs = dict(foo1='bar1', foo3=3)
    tobj = persistobj.PersistentObject(self.tmpdir, 'TestObj', **kwargs)
    tobj.Update(foo1='bar2')
    self.assertEqual(tobj.foo1, 'bar2')

  def testUpdateInlineMultiple(self):
    kwargs = dict(foo1='bar1', foo3=3)
    tobj = persistobj.PersistentObject(self.tmpdir, 'TestObj', **kwargs)
    tobj.Update(foo1='bar2', foo3=4)
    self.assertEqual(tobj.foo1, 'bar2')
    self.assertEqual(tobj.foo3, 4)

  def testUpdateInlineDict(self):
    kwargs = dict(foo1='bar1', foo3=3)
    tobj = persistobj.PersistentObject(self.tmpdir, 'TestObj', **kwargs)
    tobj.Update(**dict(foo1='bar2'))
    self.assertEqual(tobj.foo1, 'bar2')

  def testUpdateFails(self):
    kwargs = dict(foo1='bar1', foo3=3)
    tobj = persistobj.PersistentObject(self.tmpdir, 'TestObj', **kwargs)
    tobj.objdir = '/this_path_should_not_exist_hijhgvWRQ4MVVSDHuheifuh'
    kwargs['foo1'] = 'bar2'
    self.assertRaises(OSError, tobj.Update, **kwargs)

  def testGetPersistentObjects(self):
    expected = ['{"foo": "bar1", "baz": 4}',
                '{"foo": "bar2", "baz": 5}',
                '{"foo": "bar3", "baz": 6}',
                'This is not a JSON file']  # test corrupt file hanlding
    for obj in expected:
      with tempfile.NamedTemporaryFile(
          dir=self.tmpdir, prefix='tr69_dnld', delete=False) as f:
        f.write(obj)
    actual = persistobj.GetPersistentObjects(self.tmpdir)
    self.assertEqual(len(actual), len(expected)-1)
    found = [False, False, False]
    for entry in actual:
      if entry.foo == 'bar1' and entry.baz == 4:
        found[0] = True
      if entry.foo == 'bar2' and entry.baz == 5:
        found[1] = True
      if entry.foo == 'bar3' and entry.baz == 6:
        found[2] = True
    self.assertTrue(found[0])
    self.assertTrue(found[1])
    self.assertTrue(found[2])

  def testDefaultValue(self):
    kwargs = dict(foo=3)
    tobj = persistobj.PersistentObject(self.tmpdir, 'TestObj', **kwargs)
    self.assertEqual(getattr(tobj, 'foo2', 2), 2)

  def testDelete(self):
    kwargs = dict(foo1='bar1', foo3=3)
    tobj = persistobj.PersistentObject(self.tmpdir, 'TestObj', **kwargs)
    tobj.Delete()
    self.assertRaises(OSError, os.stat, tobj.filename)


if __name__ == '__main__':
  unittest.main()
