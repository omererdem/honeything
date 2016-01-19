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

"""Boolean handling for CWMP.

TR-069 Amendment 3, Annex A says:
Boolean, where the allowed values are "0", "1", "true", and "false".
The values "1" and "true" are considered interchangeable, where both
equivalently represent the logical value true. Similarly, the values
"0" and "false" are considered interchangeable, where both equivalently
represent the logical value false.
"""

__author__ = 'dgentry@google.com (Denton Gentry)'


def format(arg):
  """Print a CWMP boolean object."""
  return '1' if arg else '0'


def parse(arg):
  lower = str(arg).lower()
  if lower == 'false' or lower == '0':
    return False
  elif lower == 'true' or lower == '1':
    return True
  else:
    raise ValueError('Invalid CWMP boolean')


def valid(arg):
  # pylint: disable-msg=W0702
  try:
    parse(arg)
  except:
    return False
  return True
