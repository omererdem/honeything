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

"""A persistence layer that works with tr/core.py data structures."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import json
import sqlite3

import google3
import core


#TODO(apenwarr): consider not just using json encoding for values.
# The only offender is really 'list' type parameters, which sqlite3 can't
# store natively.  If it weren't for that, we could just use sqlite3's
# native types, which would be much more elegant.
class Store(object):
  """A data store for persisting tr.core.Exporter objects in sqlite3.

  Usage: call Load() to populate a data model hierarchy from the
  database.  Call Save() to save the data model hierarchy to the database.
  """

  def __init__(self, filename, root):
    self.filename = filename
    self.root = root
    self.db = sqlite3.connect(self.filename)
    #TODO(apenwarr): support schema versioning of some sort
    try:
      self.db.execute('create table cfg (key primary key, value)')
    except sqlite3.OperationalError:
      pass

  #TODO(apenwarr): delete objects that exist but are not in the store.
  def Load(self):
    """Load the data model objects from the database."""
    ignore_prefix = 'NOTHING'
    q = 'select key, value from cfg order by key'
    for key, json_value in self.db.execute(q):
      if key.startswith(ignore_prefix):
        print 'Skipping %s' % key
        continue
      print 'Loading %s' % key
      value = json.loads(json_value)
      if key.endswith('.'):
        # an object
        key = key[:-1]
        try:
          parent, subname = self.root.FindExport(key, allow_create=True)
        except core.NotAddableError:
          print 'Warning: %s cannot be created manually.' % key
          ignore_prefix = key
        except KeyError:
          print 'Warning: %s does not exist' % key
        else:
          print ' got %r, %r' % (parent, subname)
      else:
        # a value
        try:
          self.root.SetExportParam(key, value)
        except Exception, e:  #pylint: disable-msg=W0703
          print "Warning: can't set %r=%r:\n\t%s" % (key, value, e)

  #TODO(apenwarr): save only params marked with a "persist" flag.
  #TODO(apenwarr): invent a "persist" flag.
  def Save(self):
    """Save the data model objects into the database."""
    for key in self.root.ListExports(recursive=True):
      #TODO(apenwarr): ListExports should return a value; this is inefficient!
      if key.endswith('.'):
        value = None
      else:
        value = self.root.GetExport(key)
      try:
        self.db.execute('insert or replace into cfg (key, value) values (?,?)',
                        (key, json.dumps(value)))
      except sqlite3.InterfaceError:
        print 'sqlite3 error: key=%r value=%r' % (key, value)
        raise
    self.db.commit()
