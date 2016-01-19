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

"""Implementation of tr-181 Device.Ethernet hierarchy of objects.

Handles the Device.Ethernet portion of TR-181, as described
in http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import pynetlinux
import tr.core
import tr.cwmpdate
import tr.tr181_v2_4
import tr.x_catawampus_tr181_2_0
import netdev

BASEETHERNET = tr.tr181_v2_4.Device_v2_4.Device.Ethernet
CATAWAMPUSETHERNET = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.Device.Ethernet
PYNETIFCONF = pynetlinux.ifconfig.Interface


class EthernetInterfaceStatsLinux26(netdev.NetdevStatsLinux26,
                                    BASEETHERNET.Interface.Stats):
  """tr181 Ethernet.Interface.{i}.Stats implementation for Linux eth#."""

  def __init__(self, ifname):
    netdev.NetdevStatsLinux26.__init__(self, ifname)
    BASEETHERNET.Interface.Stats.__init__(self)


class EthernetInterfaceLinux26(CATAWAMPUSETHERNET.Interface):
  """Handling for a Linux 2.6-style device like eth0/eth1/etc.

  Constructor arguments:
    ifname: netdev name, like 'eth0'
  """

  def __init__(self, ifname, upstream=False):
    super(EthernetInterfaceLinux26, self).__init__()
    self._pynet = PYNETIFCONF(ifname)
    self._ifname = ifname
    self.Unexport('Alias')
    self.Name = ifname
    self.Upstream = upstream

  @property
  def DuplexMode(self):
    return 'Auto'

  @property
  def Enable(self):
    return True

  @property
  def LastChange(self):
    return tr.cwmpdate.format(0)

  @property
  def LowerLayers(self):
    return ''

  @property
  def MACAddress(self):
    return self._pynet.get_mac()

  @property
  def MaxBitRate(self):
    return -1

  @property
  def Status(self):
    if not self._pynet.is_up():
      return 'Down'
    (speed, duplex, auto, link_up) = self._pynet.get_link_info()
    if link_up:
      return 'Up'
    else:
      return 'Dormant'

  @property
  def Stats(self):
    return EthernetInterfaceStatsLinux26(self._ifname)

  @property
  def X_CATAWAMPUS_ORG_ActualBitRate(self):
    (speed, duplex, auto, link_up) = self._pynet.get_link_info()
    return speed

  @property
  def X_CATAWAMPUS_ORG_ActualDuplexMode(self):
    (speed, duplex, auto, link_up) = self._pynet.get_link_info()
    return 'Full' if duplex else 'Half'


def main():
  pass

if __name__ == '__main__':
  main()
