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
#pylint: disable-msg=W0404
#
"""Implement the X_GOOGLE-COM_GVSB vendor data model."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import copy
import google3
import tr.x_gvsb_1_0

# Unit tests can override these.
EPGPRIMARYFILE = '/tmp/epgprimary'
EPGSECONDARYFILE = '/tmp/epgsecondary'
GVSBCHANNELFILE = '/tmp/gvsbchannel'
GVSBKICKFILE = '/tmp/gvsbkick'
GVSBSERVERFILE = '/tmp/gvsbhost'


class GvsbConfig(object):
  """A dumb data object to store config settings."""
  pass


class Gvsb(tr.x_gvsb_1_0.X_GOOGLE_COM_GVSB_v1_1):
  """Implementation of x-gvsb.xml."""

  def __init__(self):
    super(Gvsb, self).__init__()
    self.config = self.DefaultConfig()
    self.WriteFile(EPGPRIMARYFILE, '')
    self.WriteFile(EPGSECONDARYFILE, '')
    self.WriteFile(GVSBCHANNELFILE, '')
    self.WriteFile(GVSBKICKFILE, '')
    self.WriteFile(GVSBSERVERFILE, '')

  def DefaultConfig(self):
    obj = GvsbConfig()
    obj.epgprimary = None
    obj.epgsecondary = None
    obj.gvsbserver = None
    obj.gvsb_channel_lineup = 0
    obj.gvsb_kick = None
    return obj

  def StartTransaction(self):
    config = self.config
    self.config = copy.copy(config)
    self.old_config = config

  def AbandonTransaction(self):
    self.config = self.old_config
    self.old_config = None

  def CommitTransaction(self):
    self._ConfigureGvsb()
    self.old_config = None

  def GetEpgPrimary(self):
    return self.config.epgprimary

  def SetEpgPrimary(self, value):
    self.config.epgprimary = value

  EpgPrimary = property(GetEpgPrimary, SetEpgPrimary, None,
                        'X_GVSB.EpgPrimary')

  def GetEpgSecondary(self):
    return self.config.epgsecondary

  def SetEpgSecondary(self, value):
    self.config.epgsecondary = value

  EpgSecondary = property(GetEpgSecondary, SetEpgSecondary, None,
                          'X_GVSB.EpgSecondary')

  def GetGvsbServer(self):
    return self.config.gvsbserver

  def SetGvsbServer(self, value):
    self.config.gvsbserver = value

  GvsbServer = property(GetGvsbServer, SetGvsbServer, None,
                        'X_GVSB.GvsbServer')

  def GetGvsbChannelLineup(self):
    return self.config.gvsb_channel_lineup

  def SetGvsbChannelLineup(self, value):
    self.config.gvsb_channel_lineup = int(value)

  GvsbChannelLineup = property(GetGvsbChannelLineup, SetGvsbChannelLineup, None,
                               'X_GVSB.GvsbChannelLineup')

  def GetGvsbKick(self):
    return self.config.gvsb_kick

  def SetGvsbKick(self, value):
    self.config.gvsb_kick = value

  GvsbKick = property(GetGvsbKick, SetGvsbKick, None, 'X_GVSB.GvsbKick')

  def WriteFile(self, filename, content):
    try:
      with open(filename, 'w') as f:
        f.write(content)
      return True
    except IOError:
      return False

  def _ConfigureGvsb(self):
    if self.config.epgprimary != self.old_config.epgprimary:
      if self.WriteFile(EPGPRIMARYFILE, str(self.config.epgprimary)):
        self.old_config.epgprimary = self.config.epgprimary
    if self.config.epgsecondary != self.old_config.epgsecondary:
      if self.WriteFile(EPGSECONDARYFILE, str(self.config.epgsecondary)):
        self.old_config.epgsecondary = self.config.epgsecondary
    if self.config.gvsbserver != self.old_config.gvsbserver:
      if self.WriteFile(GVSBSERVERFILE, str(self.config.gvsbserver)):
        self.old_config.gvsbserver = self.config.gvsbserver
    if self.config.gvsb_channel_lineup != self.old_config.gvsb_channel_lineup:
      if self.WriteFile(GVSBCHANNELFILE, str(self.config.gvsb_channel_lineup)):
        self.old_config.gvsb_channel_lineup = self.config.gvsb_channel_lineup
    if self.config.gvsb_kick != self.old_config.gvsb_kick:
      if self.WriteFile(GVSBKICKFILE, self.config.gvsb_kick):
        self.old_config.gvsb_kick = self.config.gvsb_kick


def main():
  pass

if __name__ == '__main__':
  main()
