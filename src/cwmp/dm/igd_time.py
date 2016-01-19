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

"""Implementation of tr-98 InternetGatewayDevice.Time
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import copy
import datetime

import tr.core
import tr.cwmpdate
import tr.tr098_v1_4


BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
TIMENOW = datetime.datetime.now


class TimeConfig(object):
  """A dumb data object to store config settings."""
  def __init__(self):
    self.TZ = None


class TimeTZ(BASE98IGD.Time):
  """An implementation of tr98 InternetGatewayDevice.Time.

  This object does not handle NTPd configuration, only CurrentLocalTime
  and LocalTimeZoneName. It writes the timezone information to /etc/TZ,
  which is generally the right thing to do for Linux uClibc systems. If the
  system is running glibc, you should not use this class.
  """

  def __init__(self, tzfile='/etc/TZ'):
    BASE98IGD.Time.__init__(self)
    self.Unexport('DaylightSavingsEnd')
    self.Unexport('DaylightSavingsStart')
    self.Unexport('DaylightSavingsUsed')
    self.Unexport('LocalTimeZone')
    self.Unexport('NTPServer1')
    self.Unexport('NTPServer2')
    self.Unexport('NTPServer3')
    self.Unexport('NTPServer4')
    self.Unexport('NTPServer5')
    self.Unexport('Status')
    self.config = TimeConfig()
    self.old_config = None
    self.tzfile = tzfile

  def StartTransaction(self):
    config = self.config
    self.config = copy.copy(config)
    self.old_config = config

  def AbandonTransaction(self):
    self.config = self.old_config
    self.old_config = None

  def CommitTransaction(self):
    self.old_config = None
    if self.config.TZ is not None:
      f = open(self.tzfile, 'w')
      # uClibc is picky about whitespace: exactly one newline, no more, no less.
      tz = str(self.config.TZ).strip() + '\n'
      f.write(tz)
      f.close()

  def GetEnable(self):
    return True

  Enable = property(GetEnable, None, None, 'InternetGatewayDevice.Time.Enable')

  def GetCurrentLocalTime(self):
    return tr.cwmpdate.format(TIMENOW())

  CurrentLocalTime = property(GetCurrentLocalTime, None, None,
                              'InternetGatewayDevice.Time.CurrentLocalTime')

  def GetLocalTimeZoneName(self):
    try:
      return open(self.tzfile, 'r').readline().strip()
    except IOError:
      return''

  def SetLocalTimeZoneName(self, value):
    self.config.TZ = value

  LocalTimeZoneName = property(GetLocalTimeZoneName, SetLocalTimeZoneName, None,
                               'InternetGatewayDevice.Time.LocalTimeZoneName')


def main():
  pass

if __name__ == '__main__':
  main()
