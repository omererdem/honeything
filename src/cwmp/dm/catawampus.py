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

"""Implementation of the x-catawampus-org vendor data model."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import json
import sys
import google3
import tr.core
import tr.x_catawampus_1_0

from src.logger.HoneythingLogging import HTLogging

ht = HTLogging()
BASEDM = tr.x_catawampus_1_0.X_CATAWAMPUS_ORG_CATAWAMPUS_v1_0


#pylint: disable-msg=W0231
class CatawampusDm(BASEDM):
  """Implementation of x-catawampus-1.0. See tr/schema/x-catawampus.xml."""

  def __init__(self):
    BASEDM.__init__(self)

  @property
  def RuntimeEnvInfo(self):
    """Return string of interesting settings from Python environment."""
    python = dict()
    python['exec_prefix'] = sys.exec_prefix
    python['executable'] = sys.executable
    python['path'] = str(sys.path)
    python['platform'] = sys.platform
    python['prefix'] = sys.prefix
    python['version'] = sys.version

    env = dict()
    env['python'] = python

    return json.dumps(env)


if __name__ == '__main__':
  sys.path.append('../')
  cm = CatawampusDm()
  #print tr.core.Dump(cm)
  ht.logger.info(tr.core.Dump(cm))
