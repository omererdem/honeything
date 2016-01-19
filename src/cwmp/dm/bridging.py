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

"""Implementation of tr-181 Device.Bridging hierarchy of objects.

Handles the Device.Bridging portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import tr.core
import tr.tr181_v2_2


BASEBRIDGE = tr.tr181_v2_2.Device_v2_2.Device.Bridging


class BridgingState(object):
  def __init__(self, brname):
    self.brname = brname


class Bridging(BASEBRIDGE):
  def __init__(self):
    BASEBRIDGE.__init__(self)
    self._Bridges = {}
    self.MaxBridgeEntries = 32
    self.MaxDBridgeEntries = 32
    self.MaxQBridgeEntries = 32
    self.MaxVLANEntries = 4096
    self.MaxFilterEntries = 0  # TODO(dgentry) figure this out

  @property
  def BridgeNumberOfEntries(self):
    return len(self.BridgeList)

  @property
  def FilterNumberOfEntries(self):
    return len(self.FilterList)


def main():
  pass

if __name__ == '__main__':
  main()
