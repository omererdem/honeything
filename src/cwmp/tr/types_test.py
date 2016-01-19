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
#
"""Tests for types.py."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import unittest
import google3
import tr.types


class TestObject(object):
  a = tr.types.Attr()
  b = tr.types.Bool()
  s = tr.types.String('defaultstring')
  i = tr.types.Int()
  u = tr.types.Unsigned()
  f = tr.types.Float(4)
  e = tr.types.Enum(['one', 'two', 'three', 7, None])
  e2 = tr.types.Enum(['thing'])


class TriggerObject(object):
  def __init__(self):
    self.xval = 7
    self.triggers = 0

  def Triggered(self):
    self.triggers += 1

  @property
  def val(self):
    return self.xval

  @tr.types.Trigger
  @val.setter
  def val(self, value):
    self.xval = value

  a = tr.types.Trigger(tr.types.Attr())
  b = tr.types.Trigger(tr.types.Bool())
  i = tr.types.Trigger(tr.types.Int())


class ReadOnlyObject(object):
  b = tr.types.ReadOnlyBool(True)
  i = tr.types.ReadOnlyInt('5')
  s = tr.types.ReadOnlyString('foo')
  e = tr.types.ReadOnlyEnum(['x', 'y', 'z'])


class TypesTest(unittest.TestCase):
  def testTypes(self):
    obj = TestObject()
    self.assertEquals(obj.a, None)
    self.assertEquals(obj.b, None)
    self.assertEquals(obj.s, 'defaultstring')
    self.assertEquals(obj.i, None)
    self.assertEquals(obj.e, None)
    self.assertEquals(obj.e2, None)
    o1 = object()

    obj.a = o1
    self.assertEquals(obj.a, o1)
    obj.a = None
    self.assertEquals(obj.a, None)

    obj.b = 0
    self.assertEquals(obj.b, 0)
    self.assertNotEqual(obj.b, None)
    obj.b = False
    self.assertEquals(obj.b, 0)
    obj.b = 'FaLSe'
    self.assertEquals(obj.b, 0)
    self.assertTrue(obj.b is False)
    self.assertTrue(obj.b is not 0)
    obj.b = 'tRuE'
    self.assertEquals(obj.b, 1)
    self.assertTrue(obj.b is True)
    self.assertTrue(obj.b is not 1)
    self.assertRaises(ValueError, setattr, obj, 'b', '5')
    self.assertRaises(ValueError, setattr, obj, 'b', '')
    self.assertRaises(ValueError, setattr, obj, 'b', object())
    self.assertRaises(ValueError, setattr, obj, 'b', [])

    self.assertEquals(obj.s, 'defaultstring')
    obj.s = 1
    self.assertEquals(obj.s, '1')
    obj.s = o1
    self.assertEquals(obj.s, str(o1))
    obj.s = None
    self.assertEquals(obj.s, None)
    self.assertNotEqual(obj.s, str(None))
    obj.s = ''
    self.assertEquals(obj.s, '')
    self.assertNotEqual(obj.s, None)

    obj.i = 7
    self.assertEquals(obj.i, 7)
    obj.i = '8'
    self.assertEquals(obj.i, 8)
    self.assertRaises(ValueError, setattr, obj, 'i', '')

    obj.u = '5'
    self.assertEquals(obj.u, 5)
    obj.u = 0
    self.assertEquals(obj.u, 0)
    self.assertRaises(ValueError, setattr, obj, 'u', '-5')
    self.assertRaises(ValueError, setattr, obj, 'u', -5)

    obj.f = '5'
    self.assertEquals(obj.f, 5.0)
    obj.f = 0
    self.assertEquals(obj.f, 0)
    obj.f = 5e60
    self.assertEquals(obj.f, 5e60)

    obj.e = 'one'
    self.assertEquals(obj.e, 'one')
    obj.e = 7
    self.assertEquals(obj.e, 7)
    self.assertRaises(ValueError, setattr, obj, 'e', '7')
    obj.e = None

    obj.e2 = 'thing'
    self.assertRaises(ValueError, setattr, obj, 'e2', None)

  def testTriggers(self):
    obj = TriggerObject()
    self.assertEquals(obj.xval, 7)
    self.assertEquals(obj.triggers, 0)

    obj.val = 99
    self.assertEquals(obj.xval, 99)
    self.assertEquals(obj.val, 99)
    self.assertEquals(obj.triggers, 1)
    obj.val = 99
    self.assertEquals(obj.triggers, 1)
    obj.val = 98
    self.assertEquals(obj.triggers, 2)

    obj.a = 5
    self.assertEquals(obj.triggers, 3)
    obj.a = '5'
    self.assertEquals(obj.triggers, 4)
    obj.a = '5'
    self.assertEquals(obj.triggers, 4)

    obj.b = 0
    self.assertEquals(obj.triggers, 5)
    obj.b = '0'
    self.assertEquals(obj.triggers, 5)
    obj.b = 'TRuE'
    self.assertEquals(obj.b, 1)
    self.assertEquals(obj.triggers, 6)

    # test that exceptions get passed through
    obj.i = 9
    self.assertEquals(obj.triggers, 7)
    self.assertRaises(ValueError, setattr, obj, 'i', '1.2')
    self.assertEquals(obj.triggers, 7)

  def testReadOnly(self):
    obj = ReadOnlyObject()
    self.assertRaises(AttributeError, setattr, obj, 'b', True)
    self.assertRaises(AttributeError, setattr, obj, 'b', False)
    self.assertEquals(obj.b, True)
    type(obj).b.Set(obj, False)
    self.assertEquals(obj.b, False)

    self.assertEquals(obj.i, 5)
    self.assertEquals(obj.s, 'foo')
    self.assertEquals(obj.e, None)
    self.assertRaises(AttributeError, setattr, obj, 'i', 5)
    self.assertRaises(AttributeError, setattr, obj, 's', 'foo')
    self.assertRaises(AttributeError, setattr, obj, 'e', None)


if __name__ == '__main__':
  unittest.main()
