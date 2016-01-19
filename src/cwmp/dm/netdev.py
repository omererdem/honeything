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

"""Implementation of network device support used in a number of data models."""

__author__ = 'dgentry@google.com (Denton Gentry)'

# Unit tests can override this.
PROC_NET_DEV = '/proc/net/dev'


class NetdevStatsLinux26(object):
  """Parses /proc/net/dev to populate Stats objects in several TRs."""

  # Fields in /proc/net/dev
  _RX_BYTES = 0
  _RX_PKTS = 1
  _RX_ERRS = 2
  _RX_DROP = 3
  _RX_FIFO = 4
  _RX_FRAME = 5
  _RX_COMPRESSED = 6
  _RX_MCAST = 7
  _TX_BYTES = 8
  _TX_PKTS = 9
  _TX_DROP = 10
  _TX_FIFO = 11
  _TX_COLLISIONS = 12
  _TX_CARRIER = 13
  _TX_COMPRESSED = 14

  def __init__(self, ifname):
    """Parse fields from a /proc/net/dev line.

    Args:
      ifname: string name of the interface, like "eth0"
    """
    ifstats = self._ReadProcNetDev(ifname)
    if ifstats:
      self.BroadcastPacketsReceived = None
      self.BroadcastPacketsSent = None
      self.BytesReceived = ifstats[self._RX_BYTES]
      self.BytesSent = ifstats[self._TX_BYTES]
      self.DiscardPacketsReceived = ifstats[self._RX_DROP]
      self.DiscardPacketsSent = ifstats[self._TX_DROP]

      err = int(ifstats[self._RX_ERRS]) + int(ifstats[self._RX_FRAME])
      self.ErrorsReceived = str(err)

      self.ErrorsSent = ifstats[self._TX_FIFO]
      self.MulticastPacketsReceived = ifstats[self._RX_MCAST]
      self.MulticastPacketsSent = None
      self.PacketsReceived = ifstats[self._RX_PKTS]
      self.PacketsSent = ifstats[self._TX_PKTS]

      rx = int(ifstats[self._RX_PKTS]) - int(ifstats[self._RX_MCAST])
      self.UnicastPacketsReceived = str(rx)

      # Linux doesn't break out transmit uni/multi/broadcast, but we don't
      # want to return None for all of them. So we return all transmitted
      # packets as unicast, though some were surely multicast or broadcast.
      self.UnicastPacketsSent = ifstats[self._TX_PKTS]
      self.UnknownProtoPacketsReceived = None

  def _ReadProcNetDev(self, ifname):
    """Return the /proc/net/dev entry for ifname.

    Args:
      ifname: string name of the interface, ecx: "eth0"

    Returns:
      The /proc/net/dev entry for ifname as a list.
    """
    f = open(PROC_NET_DEV)
    for line in f:
      fields = line.split(':')
      if (len(fields) == 2) and (fields[0].strip() == ifname):
        return fields[1].split()
    return None


def main():
  pass

if __name__ == '__main__':
  main()
