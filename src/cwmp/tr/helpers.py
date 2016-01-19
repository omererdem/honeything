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

"""Simple helper functions that don't belong elsewhere."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import errno
import os
import time
import tornado.util


def Unlink(filename):
  """Like os.unlink, but doesn't raise exception if file was missing already.

  After all, you want the file gone.  It's gone.  Stop complaining.

  Args:
    filename: the filename to delete
  Raises:
    OSError: if os.unlink() failes with other than ENOENT.
  """
  try:
    os.unlink(filename)
  except OSError, e:
    if e.errno != errno.ENOENT:
      raise


def WriteFileAtomic(tmp_file_name, final_file_name, data):
  """Writes data to tmp file, then moves it to the final file atomically."""
  with file(tmp_file_name, 'w') as f:
    f.write(data)
  os.rename(tmp_file_name, final_file_name)


def monotime():
  if hasattr(tornado.util, 'monotime'):
    return tornado.util.monotime()
  else:
    return time.time()
