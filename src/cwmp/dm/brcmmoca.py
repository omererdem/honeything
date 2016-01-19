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

"""Implementation of tr-181 MoCA objects for Broadcom chipsets."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import re
import subprocess
import pynetlinux
import tr.core
import tr.tr181_v2_2
import netdev


BASE181MOCA = tr.tr181_v2_2.Device_v2_2.Device.MoCA
MOCACTL = '/bin/mocactl'
PYNETIFCONF = pynetlinux.ifconfig.Interface


def IntOrZero(arg):
  try:
    return int(arg)
  except ValueError:
    return 0

def FloatOrZero(arg):
  try:
    return float(arg)
  except ValueError:
    return 0.0


class BrcmMocaInterface(BASE181MOCA.Interface):
  """An implementation of tr181 Device.MoCA.Interface for Broadcom chipsets."""

  def __init__(self, ifname, upstream=False):
    BASE181MOCA.Interface.__init__(self)
    self._ifname = ifname
    self.upstream = upstream
    self._pynet = PYNETIFCONF(ifname)

    self.Unexport('Alias')
    self.Unexport('MaxBitRate')
    self.Unexport('MaxIngressBW')
    self.Unexport('MaxEgressBW')
    self.Unexport('MaxNodes')
    self.Unexport('PreferredNC')
    self.Unexport('PrivacyEnabledSetting')
    self.Unexport('FreqCapabilityMask')
    self.Unexport('FreqCurrentMaskSetting')
    self.Unexport('FreqCurrentMask')
    self.Unexport('KeyPassphrase')
    self.Unexport('TxPowerLimit')
    self.Unexport('PowerCntlPhyTarget')
    self.Unexport('BeaconPowerLimit')
    self.Unexport('NetworkTabooMask')
    self.Unexport('NodeTabooMask')
    self.Unexport('TxBcastRate')
    self.Unexport('TxBcastPowerReduction')
    self.Unexport(objects='QoS')

    self.AssociatedDeviceList = tr.core.AutoDict(
        'AssociatedDeviceList', iteritems=self.IterAssociatedDevices,
        getitem=self.GetAssociatedDeviceByIndex)

  @property  # TODO(dgentry) need @sessioncache decorator.
  def Stats(self):
    return BrcmMocaInterfaceStatsLinux26(self._ifname)

  # TODO(dgentry) need @sessioncache decorator
  def _MocaCtlShowStatus(self):
    """Return output of mocactl show --status."""
    mc = subprocess.Popen([MOCACTL, 'show', '--status'], stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    return out.splitlines()

  # TODO(dgentry) need @sessioncache decorator
  def _MocaCtlShowInitParms(self):
    """Return output of mocactl show --initparms."""
    mc = subprocess.Popen([MOCACTL, 'show', '--initparms'],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    return out.splitlines()

  # TODO(dgentry) need @sessioncache decorator
  def _MocaCtlShowConfig(self):
    """Return output of mocactl show --config."""
    mc = subprocess.Popen([MOCACTL, 'show', '--config'], stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    return out.splitlines()

  def _MocaCtlGetField(self, outfcn, field):
    """Look for one field in a mocactl command.

    ex: field='SwVersion' would return 5.6.789 from
    vendorId              : 999999999   HwVersion             : 0x12345678
    SwVersion             : 5.6.789     self MoCA Version     : 0x11

    Args:
      outfcn: a function to call, which must return a list of text lines.
      field: the text string to look for.
    Returns:
      The value of the field, or None.
    """

    m_re = re.compile(field + '\s*:\s+(\S+)')
    for line in outfcn():
      mr = m_re.search(line)
      if mr is not None:
        return mr.group(1)
    return None

  @property
  def Enable(self):
    # TODO(dgentry) Supposed to be read/write, but we don't disable yet.
    return True

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
  def Name(self):
    return self._ifname

  @property
  def LastChange(self):
    up = self._MocaCtlGetField(self._MocaCtlShowStatus, 'linkUpTime').split(':')
    secs = 0
    for t in up:
      # linkUpTime ex: '23h:41m:30s'
      num = IntOrZero(t[:-1])
      if t[-1] == 'y':
        secs += int(num * (365.25 * 24.0 * 60.0 * 60.0))
      elif t[-1] == 'w':
        secs += num * (7 * 24 * 60 * 60)
      elif t[-1] == 'd':
        secs += num * (24 * 60 * 60)
      elif t[-1] == 'h':
        secs += num * (60 * 60)
      elif t[-1] == 'm':
        secs += num * 60
      elif t[-1] == 's':
        secs += num
    return secs

  @property
  def LowerLayers(self):
    # In theory this is writeable, but it is nonsensical to write to it.
    return ''

  @property
  def Upstream(self):
    return self.upstream

  @property
  def MACAddress(self):
    return self._pynet.get_mac()

  @property
  def FirmwareVersion(self):
    ver = self._MocaCtlGetField(self._MocaCtlShowStatus, 'SwVersion')
    return ver if ver else '0'

  def _RegToMoCA(self, regval):
    moca = {'0x10': '1.0', '0x11': '1.1', '0x20': '2.0', '0x21': '2.1'}
    return moca.get(regval, '0.0')

  @property
  def HighestVersion(self):
    reg = self._MocaCtlGetField(self._MocaCtlShowStatus, 'self MoCA Version')
    return self._RegToMoCA(reg)

  @property
  def CurrentVersion(self):
    reg = self._MocaCtlGetField(self._MocaCtlShowStatus, 'networkVersionNumber')
    return self._RegToMoCA(reg)

  @property
  def NetworkCoordinator(self):
    nodeid = self._MocaCtlGetField(self._MocaCtlShowStatus, 'ncNodeId')
    return IntOrZero(nodeid)

  @property
  def NodeID(self):
    nodeid = self._MocaCtlGetField(self._MocaCtlShowStatus, 'nodeId')
    return IntOrZero(nodeid)

  @property
  def BackupNC(self):
    bnc = nodeid = self._MocaCtlGetField(self._MocaCtlShowStatus, 'backupNcId')
    return bnc if bnc else ''

  @property
  def PrivacyEnabled(self):
    private = self._MocaCtlGetField(self._MocaCtlShowInitParms, 'Privacy')
    return True if private == 'enabled' else False

  @property
  def CurrentOperFreq(self):
    freq = self._MocaCtlGetField(self._MocaCtlShowStatus, 'rfChannel')
    if freq:
      return IntOrZero(freq.split()[0])
    return 0

  @property
  def LastOperFreq(self):
    last = self._MocaCtlGetField(self._MocaCtlShowInitParms,
                                 'Nv Params - Last Oper Freq')
    if last:
      return IntOrZero(last.split()[0])
    return 0

  @property
  def QAM256Capable(self):
    qam = self._MocaCtlGetField(self._MocaCtlShowInitParms, 'qam256Capability')
    return True if qam == 'on' else False

  @property
  def PacketAggregationCapability(self):
    # example: "maxPktAggr   : 10 pkts"
    pkts = self._MocaCtlGetField(self._MocaCtlShowConfig, 'maxPktAggr')
    if pkts:
      return IntOrZero(pkts.split()[0])
    return 0

  @property
  def AssociatedDeviceNumberOfEntries(self):
    return len(self.AssociatedDeviceList)

  def _MocaCtlGetNodeIDs(self):
    """Return a list of active MoCA Node IDs."""
    mc = subprocess.Popen([MOCACTL, 'showtbl', '--nodestats'],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    node_re = re.compile('\ANode\s*: (\d+)')
    nodes = set()
    for line in out.splitlines():
      node = node_re.search(line)
      if node is not None:
        nodes.add(int(node.group(1)))
    return list(nodes)

  def GetAssociatedDevice(self, nodeid):
    """Get an AssociatedDevice object for the given NodeID."""
    ad = BrcmMocaAssociatedDevice(nodeid)
    if ad:
      ad.ValidateExports()
    return ad

  def IterAssociatedDevices(self):
    """Retrieves a list of all associated devices."""
    mocanodes = self._MocaCtlGetNodeIDs()
    for idx, nodeid in enumerate(mocanodes):
      yield idx, self.GetAssociatedDevice(nodeid)

  def GetAssociatedDeviceByIndex(self, index):
    mocanodes = self._MocaCtlGetNodeIDs()
    return self.GetAssociatedDevice(mocanodes[index])


class BrcmMocaInterfaceStatsLinux26(netdev.NetdevStatsLinux26,
                                    BASE181MOCA.Interface.Stats):
  """tr181 Device.MoCA.Interface.Stats for Broadcom chipsets."""

  def __init__(self, ifname):
    netdev.NetdevStatsLinux26.__init__(self, ifname)
    BASE181MOCA.Interface.Stats.__init__(self)


class BrcmMocaAssociatedDevice(BASE181MOCA.Interface.AssociatedDevice):
  """tr-181 Device.MoCA.Interface.AssociatedDevice for Broadcom chipsets."""

  def __init__(self, nodeid):
    BASE181MOCA.Interface.AssociatedDevice.__init__(self)
    self.NodeID = nodeid
    self.MACAddress = ''
    self.PreferredNC = False
    self.Unexport('HighestVersion')
    self.PHYTxRate = 0
    self.PHYRxRate = 0
    self.TxPowerControlReduction = 0
    self.RxPowerLevel = 0
    self.TxBcastRate = 0
    self.RxBcastPowerLevel = 0
    self.TxPackets = 0
    self.RxPackets = 0
    self.RxErroredAndMissedPackets = 0
    self.QAM256Capable = 0
    self.PacketAggregationCapability = 0
    self.RxSNR = 0
    self.Unexport('Active')

    self.ParseNodeStatus()
    self.ParseNodeStats()

  def ParseNodeStatus(self):
    """Run mocactl show --nodestatus for this node, parse the output."""
    mac_re = re.compile(
        '^MAC Address\s+: ((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})')
    pnc_re = re.compile('Preferred NC\s+: (\d+)')
    ptx_re = re.compile('\ATxUc.+?(\d+[.]?\d*)\s+dBm.*?(\d+)\s+bps')
    prx_re = re.compile('\ARxUc.+?(\d+[.]?\d*)\s+dBm.*?(\d+)\s+bps'
                        '\s+(\d+[.]?\d*) dB')
    rxb_re = re.compile('\ARxBc.+?(\d+[.]?\d*)\s+dBm.*?(\d+)\s+bps')
    qam_re = re.compile('256 QAM capable\s+:\s+(\d+)')
    agg_re = re.compile('Aggregated PDUs\s+:\s+(\d+)')
    mc = subprocess.Popen([MOCACTL, 'show', '--nodestatus', str(self.NodeID)],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    for line in out.splitlines():
      mac = mac_re.search(line)
      if mac is not None:
        self.MACAddress = mac.group(1)
      pnc = pnc_re.search(line)
      if pnc is not None:
        self.PreferredNC = False if pnc.group(1) is '0' else True
      ptx = ptx_re.search(line)
      if ptx is not None:
        self.PHYTxRate = IntOrZero(ptx.group(2)) / 1000000
        self.TxPowerControlReduction = int(FloatOrZero(ptx.group(1)))
      prx = prx_re.search(line)
      if prx is not None:
        self.PHYRxRate = IntOrZero(prx.group(2)) / 1000000
        self.RxPowerLevel = int(FloatOrZero(prx.group(1)))
        # TODO(dgentry) This cannot be right. SNR should be dB, not an integer.
        self.RxSNR = int(FloatOrZero(prx.group(3)))
      rxb = rxb_re.search(line)
      if rxb is not None:
        self.TxBcastRate = IntOrZero(rxb.group(2)) / 1000000
        self.RxBcastPowerLevel = int(FloatOrZero(rxb.group(1)))
      qam = qam_re.search(line)
      if qam is not None:
        self.QAM256Capable = False if qam.group(1) is '0' else True
      agg = agg_re.search(line)
      if agg is not None:
        self.PacketAggregationCapability = IntOrZero(agg.group(1))

  def ParseNodeStats(self):
    """Run mocactl show --nodestats for this node, parse the output."""
    tx_re = re.compile('Unicast Tx Pkts To Node\s+: (\d+)')
    rx_re = re.compile('Unicast Rx Pkts From Node\s+: (\d+)')
    e1_re = re.compile('Rx CodeWord ErrorAndUnCorrected\s+: (\d+)')
    e2_re = re.compile('Rx NoSync Errors\s+: (\d+)')
    mc = subprocess.Popen([MOCACTL, 'show', '--nodestats', str(self.NodeID)],
                          stdout=subprocess.PIPE)
    out, _ = mc.communicate(None)
    rx_err = 0
    for line in out.splitlines():
      tx = tx_re.search(line)
      if tx is not None:
        self.TxPackets = IntOrZero(tx.group(1))
      rx = rx_re.search(line)
      if rx is not None:
        self.RxPackets = IntOrZero(rx.group(1))
      e1 = e1_re.search(line)
      if e1 is not None:
        rx_err += IntOrZero(e1.group(1))
      e2 = e2_re.search(line)
      if e2 is not None:
        rx_err += IntOrZero(e2.group(1))
    self.RxErroredAndMissedPackets = rx_err


class BrcmMoca(BASE181MOCA):
  """An implementation of tr181 Device.MoCA for Broadcom chipsets."""

  def __init__(self):
    BASE181MOCA.__init__(self)
    self.InterfaceList = {}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)


def main():
  pass

if __name__ == '__main__':
  main()
