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
#pylint: disable-msg=C6409,W0212
#
"""Type descriptors for common TR-069 data types."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


class Attr(object):
  """A descriptor that holds an arbitrary attribute.

  This isn't very useful on its own, but we declare type-specific child
  classes that enforce the data type.  For example:

    class X(object):
      a = Attr()
      b = Bool()
      s = String()
      i = Int()
      e = Enum('Bob', 'Fred')
    x = X()
    x.a = object()
    x.b = '0'    # actually gets set to integer 0
    x.s = [1,2]  # gets set to the string str([1, 2])
    x.i = '9'    # auto-converts to a real int
    x.e = 'Stinky'  # raises exception since it's not an allowed value
  """

  def __init__(self, init=None):
    self.init = init

  def _MakeAttrs(self, obj):
    try:
      return obj.__Attrs
    except AttributeError:
      obj.__Attrs = {}
      return obj.__Attrs

  def __get__(self, obj, _):
    # Type descriptors (ie. this class) are weird because they only have
    # one instance per member of a class, not per member of an *object*.
    # That is, all the objects of a given class share the same type
    # descriptor instance.  Thus, we have to store the actual property
    # value in a hidden variable in each obj, rather than in self.
    if obj is None:
      return self
    d = self._MakeAttrs(obj)
    try:
      return d[id(self)]
    except KeyError:
      if self.init is not None:
        self.__set__(obj, self.init)
      else:
        # special case: if init==None, don't do consistency checking, in
        # order to support initially-invalid variables
        d[id(self)] = self.init
      return d[id(self)]

  def __set__(self, obj, value):
    d = self._MakeAttrs(obj)
    d[id(self)] = value


class Bool(Attr):
  """An attribute that is always either 0 or 1.

  You can set it to the strings 'true' or 'false' (case insensitive) or
  '0' or '1' or the numbers 0, 1, True, or False.
  """

  def __set__(self, obj, value):
    s = str(value).lower()
    if s in ('true', '1'):
      Attr.__set__(self, obj, True)
    elif s in ('false', '0'):
      Attr.__set__(self, obj, False)
    else:
      raise ValueError('%r is not a valid boolean' % value)


class Int(Attr):
  """An attribute that is always an integer."""

  def __set__(self, obj, value):
    Attr.__set__(self, obj, int(value))


class Unsigned(Attr):
  """An attribute that is always an integer >= 0."""

  def __set__(self, obj, value):
    v = int(value)
    if v < 0:
      raise ValueError('%r must be >= 0' % value)
    Attr.__set__(self, obj, v)


class Float(Attr):
  """An attribute that is always a floating point number."""

  def __set__(self, obj, value):
    Attr.__set__(self, obj, float(value))


class String(Attr):
  """An attribute that is always a string or None."""

  def __set__(self, obj, value):
    if value is None:
      Attr.__set__(self, obj, None)
    else:
      Attr.__set__(self, obj, str(value))


class Enum(Attr):
  """An attribute that is always one of the given values.

  The values are usually strings in TR-069, but this is not enforced.
  """

  def __init__(self, values, init=None):
    super(Enum, self).__init__(init=init)
    self.values = set(values)

  def __set__(self, obj, value):
    if value not in self.values:
      raise ValueError('%r invalid; value values are %r'
                       % (value, self.values))
    Attr.__set__(self, obj, value)


class Trigger(object):
  """A type descriptor that calls obj.Triggered() whenever its value changes.

  The 'attr' parameter to __init__ must be a descriptor itself.  So it
  could be an object derived from Attr (above), or an @property.  Examples:

    class X(object):
      def __init__(self):
        self._thing = 7
      def Triggered(self):
        print 'woke up!'
      a = Trigger(Attr())
      b = Trigger(Bool())

      @property
      def thing(self):
        return self._thing

      @Trigger
      @thing.setter
      def thing(self, value):
        self._thing = value

    x = X()
    x.a = 'hello'  # triggers
    x.a = 'hello'  # unchanged: no trigger
    b = False      # default value was None, so triggers
    b = '0'        # still false; no trigger
    thing = 7      # same as original value; no trigger
    thing = None   # triggers
  """

  def __init__(self, attr):
    self.attr = attr

  def __get__(self, obj, _):
    if obj is None:
      return self
    return self.attr.__get__(obj, None)

  def __set__(self, obj, value):
    old = self.__get__(obj, None)
    self.attr.__set__(obj, value)
    new = self.__get__(obj, None)
    if old != new:
      # the attr's __set__ function might have rejected the change; only
      # call Triggered if it *really* changed.
      obj.Triggered()


def TriggerBool(*args, **kwargs):
  return Trigger(Bool(*args, **kwargs))


def TriggerInt(*args, **kwargs):
  return Trigger(Int(*args, **kwargs))


def TriggerUnsigned(*args, **kwargs):
  return Trigger(Int(*args, **kwargs))


def TriggerFloat(*args, **kwargs):
  return Trigger(Int(*args, **kwargs))


def TriggerString(*args, **kwargs):
  return Trigger(String(*args, **kwargs))


def TriggerEnum(*args, **kwargs):
  return Trigger(Enum(*args, **kwargs))


class ReadOnly(object):
  """A type descriptor that prevents setting the wrapped Attr().

  Since usually *someone* needs to be able to set the value, we also add a
  Set() method that overrides the read-only-ness.  The syntax for doing it
  is a little weird, which is a good reminder that you're not supposed to
  change read-only objects.

  Example:
    class X(object):
      b = ReadOnly(Bool(True))

    x = X()
    print x.b          # True
    x.b = False        # raises AttributeError
    X.b.Set(x, False)  # actually sets the bool
  """

  def __init__(self, attr):
    self.attr = attr

  def __get__(self, obj, _):
    if obj is None:
      return self
    return self.attr.__get__(obj, None)

  def __set__(self, obj, _):
    # this is the same exception raised by a read-only @property
    raise AttributeError("can't set attribute")

  def Set(self, obj, value):
    """Override the read-only-ness; generally for internal use."""
    return self.attr.__set__(obj, value)


def ReadOnlyBool(*args, **kwargs):
  return ReadOnly(Bool(*args, **kwargs))


def ReadOnlyInt(*args, **kwargs):
  return ReadOnly(Int(*args, **kwargs))


def ReadOnlyUnsigned(*args, **kwargs):
  return ReadOnly(Unsigned(*args, **kwargs))


def ReadOnlyFloat(*args, **kwargs):
  return ReadOnly(Float(*args, **kwargs))


def ReadOnlyString(*args, **kwargs):
  return ReadOnly(String(*args, **kwargs))


def ReadOnlyEnum(*args, **kwargs):
  return ReadOnly(Enum(*args, **kwargs))
