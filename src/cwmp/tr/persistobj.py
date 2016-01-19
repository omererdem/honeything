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

"""Persistent objects; objects which store themselves to disk."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import glob
import json
import os
import tempfile


class PersistentObject(object):
  """Object holding simple data fields which can persist itself to json."""

  def __init__(self, objdir, rootname='object', filename=None,
               ignore_errors=False, **kwargs):
    """Create either a fresh new object, or restored state from filesystem.

    Raises:
      ValueError: reading an object from a JSON file failed.

    Args:
      objdir: the directory to write the json file to
      rootname: the tag for the root of the json file for this object.
      filename: name of an json file on disk, to restore object state from.
        If filename is None then this is a new object, and will create
        a file for itself in dir.
      ignore_errors: True if you want to ignore common errors (like read-only
        or nonexistent directories) when saving/loading state.
        Otherwise this object will raise exceptions in those cases.
      kwargs parameters will be passed to self.Update
    """

    self.objdir = objdir
    self.rootname = rootname
    self._fields = {}
    self.ignore_errors = ignore_errors
    if filename:
      self._ReadFromFS(filename)
    else:
      prefix = rootname + '_'
      try:
        f = tempfile.NamedTemporaryFile(mode='a+', prefix=prefix,
                                        dir=objdir, delete=False)
      except OSError:
        if self.ignore_errors:
          filename = objdir
        else:
          raise
      else:
        filename = f.name
        f.close()
    self.filename = filename
    if kwargs:
      self.Update(**kwargs)

  def __getattr__(self, name):
    try:
      return self.__getitem__(name)
    except KeyError:
      raise AttributeError

  def __getitem__(self, name):
    return self._fields[str(name)]

  def __str__(self):
    return self._ToJson()

  def __unicode__(self):
    return self.__str__()

  def Update(self, **kwargs):
    """Atomically update one or more parameters of the object.

    One might reasonably ask why this is an explicit call and not just
    setting parameters like self.foo="Bar". The motivation is atomicity.
    We want the state saved to the filesystem to be consistent, and not
    write out a partially updated object each time a parameter is changed.

    When this call returns, the state has been safely written to the
    filesystem. Any errors are reported by raising an exception.

    Args:
      **kwargs: Parameters to be updated.
    """
    self._fields.update(kwargs)
    self._WriteToFS()

  def Get(self, name):
    return self._fields.get(name, None)

  def values(self):
    return self._fields.values()

  def items(self):
    return self._fields.items()




  def _ToJson(self):
    for k, v in self._fields.items():
        #print k + "->" + str(type(v))
        if type(v) is not str and type(v) is not int:
            self._fields[k] = ""

    # d = {'username': [], 'delay_seconds': 0, 'url': 'http://ftp.linux.org.tr/epel/fullfilelist', 'file_type': '3 Vendor Configuration File', 'event_code': 'M Download', 'file_size': 0, 'command_key': [], 'target_filename': [], 'password': []}
    # return json.dumps(d, indent=2)
    return json.dumps(self._fields, indent=2)




  def _FromJson(self, string):
    d = json.loads(str(string))
    assert isinstance(d, dict)
    return d

  def _ReadFromFS(self, filename):
    """Read a json file back to an PersistentState object."""
    d = self._FromJson(open(filename).read())
    self._fields.update(d)

  def _WriteToFS(self):
    """Write PersistentState object out to a json file."""
    try:
      f = tempfile.NamedTemporaryFile(
          mode='a+', prefix='tmpwrite', dir=self.objdir, delete=False)
    except OSError:
      if not self.ignore_errors:
        raise
    else:
      f.write(self._ToJson())
      f.close()
      os.rename(f.name, self.filename)

  def Delete(self):
    """Remove backing file from filesystem, immediately."""
    os.remove(self.filename)


def GetPersistentObjects(objdir, rootname=''):
  globstr = objdir + '/' + rootname + '*'
  objs = []
  for filename in glob.glob(globstr):
    try:
      obj = PersistentObject(objdir, rootname=rootname, filename=filename)
    except ValueError:
      os.remove(filename)
      continue
    objs.append(obj)
  return objs


def main():
  pass

if __name__ == '__main__':
  main()
