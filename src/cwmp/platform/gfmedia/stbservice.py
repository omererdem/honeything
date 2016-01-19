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

"""Implementation of tr-135 STBService."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import glob
import json
import os
import re
import socket
import struct

import tr.cwmp_session as cwmp_session
import tr.cwmpdate
import tr.tr135_v1_2
import tr.x_catawampus_videomonitoring_1_0 as vmonitor


BASE135STB = tr.tr135_v1_2.STBService_v1_2.STBService
BASEPROGMETADATA = vmonitor.X_CATAWAMPUS_ORG_STBVideoMonitoring_v1_0.STBService
IGMPREGEX = re.compile('^\s+(\S+)\s+\d\s+\d:[0-9A-Fa-f]+\s+\d')
IGMP6REGEX = re.compile(('^\d\s+\S+\s+([0-9A-Fa-f]{32})\s+\d\s+[0-9A-Fa-f]'
                         '+\s+\d'))
PROCNETIGMP = '/proc/net/igmp'
PROCNETIGMP6 = '/proc/net/igmp6'

CONT_MONITOR_FILES = [
    '/tmp/cwmp/monitoring/ts/tr_135_total_tsstats*.json',
    '/tmp/cwmp/monitoring/dejittering/tr_135_total_djstats*.json']
EPG_STATS_FILES = ['/tmp/cwmp/monitoring/epg/tr_135_epg_stats*.json']
HDMI_STATS_FILE = '/tmp/cwmp/monitoring/hdmi/tr_135_hdmi_stats*.json'
HDMI_DISPLAY_DEVICE_STATS_FILES = [
    '/tmp/cwmp/monitoring/hdmi/tr_135_dispdev_status*.json',
    '/tmp/cwmp/monitoring/hdmi/tr_135_dispdev_stats*.json']


class STBService(BASE135STB):
  """STBService.{i}."""

  def __init__(self):
    super(STBService, self).__init__()
    self.Unexport('Alias')
    self.Unexport('Enable')
    self.Unexport(objects='AVPlayers')
    self.Unexport(objects='AVStreams')
    self.Unexport(objects='Applications')
    self.Unexport(objects='Capabilities')
    self.Export(objects=['X_CATAWAMPUS-ORG_ProgramMetadata'])
    self.ServiceMonitoring = ServiceMonitoring()
    self.Components = Components()
    self.X_CATAWAMPUS_ORG_ProgramMetadata = ProgMetadata()


class Components(BASE135STB.Components):
  """STBService.{i}.Components."""

  def __init__(self):
    super(Components, self).__init__()
    self.Unexport('AudioDecoderNumberOfEntries')
    self.Unexport('AudioOutputNumberOfEntries')
    self.Unexport('CANumberOfEntries')
    self.Unexport('DRMNumberOfEntries')
    self.Unexport('SCARTNumberOfEntries')
    self.Unexport('SPDIFNumberOfEntries')
    self.Unexport('VideoDecoderNumberOfEntries')
    self.Unexport('VideoOutputNumberOfEntries')
    self.Unexport(objects='PVR')
    self.Unexport(lists='AudioDecoder')
    self.Unexport(lists='AudioOutput')
    self.Unexport(lists='CA')
    self.Unexport(lists='DRM')
    self.Unexport(lists='SCART')
    self.Unexport(lists='SPDIF')
    self.Unexport(lists='VideoDecoder')
    self.Unexport(lists='VideoOutput')
    self.FrontEndList = {'1': FrontEnd()}
    self.HDMIList = {'1': HDMI()}

  @property
  def FrontEndNumberOfEntries(self):
    return len(self.FrontEndList)

  @property
  def HDMINumberOfEntries(self):
    return len(self.HDMIList)


class FrontEnd(BASE135STB.Components.FrontEnd):
  """STBService.{i}.Components.FrontEnd.{i}."""

  def __init__(self):
    super(FrontEnd, self).__init__()
    self.Unexport('Alias')
    self.Unexport('Enable')
    self.Unexport('Name')
    self.Unexport('Status')
    self.Unexport(objects='DVBT')
    self.IP = IP()


class IP(BASE135STB.Components.FrontEnd.IP):
  """STBService.{i}.Components.FrontEnd.{i}.IP."""

  def __init__(self):
    super(IP, self).__init__()
    self.Unexport('ActiveInboundIPStreams')
    self.Unexport('ActiveOutboundIPStreams')
    self.Unexport('InboundNumberOfEntries')
    self.Unexport('OutboundNumberOfEntries')
    self.Unexport(objects='Dejittering')
    self.Unexport(objects='RTCP')
    self.Unexport(objects='RTPAVPF')
    self.Unexport(objects='ServiceConnect')
    self.Unexport(objects='FEC')
    self.Unexport(objects='ForceMonitor')
    self.Unexport(lists='Inbound')
    self.Unexport(lists='Outbound')
    self.IGMP = IGMP()


class IGMP(BASE135STB.Components.FrontEnd.IP.IGMP):
  """STBService.{i}.Components.FrontEnd.{i}.IP.IGMP."""

  def __init__(self):
    super(IGMP, self).__init__()
    self.Unexport('ClientGroupStatsNumberOfEntries')
    self.Unexport('ClientRobustness')
    self.Unexport('ClientUnsolicitedReportInterval')
    self.Unexport('ClientVersion')
    self.Unexport('DSCPMark')
    self.Unexport('Enable')
    self.Unexport('EthernetPriorityMark')
    self.Unexport('LoggingEnable')
    self.Unexport('MaximumNumberOfConcurrentGroups')
    self.Unexport('MaximumNumberOfTrackedGroups')
    self.Unexport('Status')
    self.Unexport('VLANIDMark')
    self.Unexport(lists='ClientGroupStats')

    self.ClientGroupList = tr.core.AutoDict(
        'ClientGroupList', iteritems=self.IterClientGroups,
        getitem=self.GetClientGroupByIndex)

  @property
  def ClientGroupNumberOfEntries(self):
    return len(self.ClientGroupList)

  def _ParseProcIgmp(self):
    """Returns a list of current IGMP group memberships.

    /proc/net/igmp uses an unusual format:
    Idx Device    : Count Querier       Group    Users Timer    Reporter
    1   lo        :     1      V3
                                010000E0     1 0:00000000           0
    2   eth0      :     1      V3
                                010000E0     1 0:00000000           0
    010000E0 is the IP multicast address as a hex number, and always
    big endian.
    """
    igmps = set()
    with open(PROCNETIGMP, 'r') as f:
      for line in f:
        result = IGMPREGEX.match(line)
        if result is not None:
          igmp = result.group(1).strip()
          igmps.add(socket.inet_ntop(
              socket.AF_INET, struct.pack('<L', int(igmp, 16))))
    with open(PROCNETIGMP6, 'r') as f:
      for line in f:
        result = IGMP6REGEX.match(line)
        if result is not None:
          igmp = result.group(1).strip()
          ip6 = ':'.join([igmp[0:4], igmp[4:8], igmp[8:12], igmp[12:16],
                          igmp[16:20], igmp[20:24], igmp[24:28], igmp[28:]])
          igmps.add(socket.inet_ntop(socket.AF_INET6,
                                     socket.inet_pton(socket.AF_INET6, ip6)))
    return list(igmps)

  def GetClientGroup(self, ipaddr):
    return ClientGroup(ipaddr)

  def IterClientGroups(self):
    """Retrieves a list of IGMP memberships."""
    igmps = self._ParseProcIgmp()
    for idx, ipaddr in enumerate(igmps, start=1):
      yield str(idx), self.GetClientGroup(ipaddr)

  def GetClientGroupByIndex(self, index):
    igmps = self._ParseProcIgmp()
    i = int(index) - 1
    if i > len(igmps):
      raise IndexError('No such object ClientGroup.{0}'.format(index))
    return self.GetClientGroup(igmps[i])


class ClientGroup(BASE135STB.Components.FrontEnd.IP.IGMP.ClientGroup):
  """STBService.{i}.Components.FrontEnd.{i}.IP.IGMP.ClientGroup.{i}."""

  def __init__(self, ipaddr):
    super(ClientGroup, self).__init__()
    self.Unexport('UpTime')
    self.Unexport('Alias')
    self.ipaddr = ipaddr

  @property
  def GroupAddress(self):
    return self.ipaddr


class HDMI(BASE135STB.Components.HDMI):
  """STBService.{i}.Components.HDMI."""

  def __init__(self):
    super(HDMI, self).__init__()
    self.Unexport('Alias')
    self.Unexport('Enable')
    self.Unexport('Status')
    self.Unexport('Name')
    self.DisplayDevice = HDMIDisplayDevice()

  @property
  @cwmp_session.cache
  def _GetStats(self):
    data = dict()
    for filename in glob.glob(HDMI_STATS_FILE):
      try:
        with open(filename) as f:
          d = json.load(f)
          hdmiStats = d['HDMIStats']

          if 'ResolutionValue' in hdmiStats.keys():
            data['ResolutionValue'] = hdmiStats['ResolutionValue']

      # IOError - Failed to open file or failed to read from file
      # ValueError - JSON file is malformed and cannot be decoded
      # KeyError - Decoded JSON file doesn't contain the required fields.
      except (IOError, ValueError, KeyError) as e:
        print('HDMIStats: Failed to read stats from file {0}, '
              'error = {1}'.format(filename, e))
    return data

  @property
  def ResolutionMode(self):
    return 'Auto'

  @property
  def ResolutionValue(self):
    return self._GetStats.get('ResolutionValue', '')


class HDMIDisplayDevice(BASE135STB.Components.HDMI.DisplayDevice):
  """STBService.{i}.Components.HDMI.{i}.DisplayDevice."""

  def __init__(self):
    super(HDMIDisplayDevice, self).__init__()
    self.Unexport('CECSupport')
    self.Export(params=['X_GOOGLE-COM_NegotiationCount4'])
    self.Export(params=['X_GOOGLE-COM_NegotiationCount24'])
    self.Export(params=['X_GOOGLE-COM_VendorId'])
    self.Export(params=['X_GOOGLE-COM_ProductId'])
    self.Export(params=['X_GOOGLE-COM_MfgYear'])
    self.Export(params=['X_GOOGLE-COM_LastUpdateTimestamp'])
    self.Export(params=['X_GOOGLE-COM_EDIDExtensions'])

  @property
  @cwmp_session.cache
  def _GetStats(self):
    data = dict()
    for wildcard in HDMI_DISPLAY_DEVICE_STATS_FILES:
      for filename in glob.glob(wildcard):
        try:
          with open(filename) as f:
            d = json.load(f)
            displayStats = d['HDMIDisplayDevice']

            if 'Status' in displayStats.keys():
              data['Status'] = displayStats['Status']
            if 'Name' in displayStats.keys():
              data['Name'] = displayStats['Name']
            if 'EEDID' in displayStats.keys():
              data['EEDID'] = displayStats['EEDID']
            if 'EDIDExtensions' in displayStats.keys():
              data['EDIDExtensions'] = ', '.join(displayStats['EDIDExtensions'])
            # Supported resolutions can have duplicates! Handle it!
            if 'SupportedResolutions' in displayStats.keys():
              sup_res = set()
              for v in displayStats['SupportedResolutions']:
                sup_res.add(v)
              data['SupportedResolutions'] = ', '.join(sorted(sup_res))
            if 'PreferredResolution' in displayStats.keys():
              data['PreferredResolution'] = displayStats['PreferredResolution']
            if 'VideoLatency' in displayStats.keys():
              data['VideoLatency'] = displayStats['VideoLatency']
            if 'AutoLipSyncSupport' in displayStats.keys():
              data['AutoLipSyncSupport'] = displayStats['AutoLipSyncSupport']
            if 'HDMI3DPresent' in displayStats.keys():
              data['HDMI3DPresent'] = displayStats['HDMI3DPresent']
            if 'Negotiations4hr' in displayStats.keys():
              data['Negotiations4hr'] = displayStats['Negotiations4hr']
              data['LastUpdateTime'] = os.path.getmtime(filename)
            if 'Negotiations24hr' in displayStats.keys():
              data['Negotiations24hr'] = displayStats['Negotiations24hr']
            if 'VendorId' in displayStats.keys():
              data['VendorId'] = displayStats['VendorId']
            if 'ProductId' in displayStats.keys():
              data['ProductId'] = displayStats['ProductId']
            if 'MfgYear' in displayStats.keys():
              data['MfgYear'] = displayStats['MfgYear']

        # IOError - Failed to open file or failed to read from file
        # ValueError - JSON file is malformed and cannot be decoded
        # KeyError - Decoded JSON file doesn't contain the required fields.
        # OSError - mtime call failed.
        except (IOError, ValueError, KeyError, OSError) as e:
          print('HDMIStats: Failed to read stats from file {0}, '
                'error = {1}'.format(filename, e))

    return data

  @property
  def Status(self):
    return self._GetStats.get('Status', 'None')

  @property
  def Name(self):
    return self._GetStats.get('Name', '')

  @property
  def SupportedResolutions(self):
    return self._GetStats.get('SupportedResolutions', '')

  @property
  def EEDID(self):
    return self._GetStats.get('EEDID', '')

  @property
  def X_GOOGLE_COM_EDIDExtensions(self):
    return self._GetStats.get('EDIDExtensions', '')

  @property
  def PreferredResolution(self):
    return self._GetStats.get('PreferredResolution', '')

  @property
  def VideoLatency(self):
    return self._GetStats.get('VideoLatency', 0)

  @property
  def AutoLipSyncSupport(self):
    return self._GetStats.get('AutoLipSyncSupport', False)

  @property
  def HDMI3DPresent(self):
    return self._GetStats.get('HDMI3DPresent', False)

  @property
  def X_GOOGLE_COM_NegotiationCount4(self):
    return self._GetStats.get('Negotiations4hr', 0)

  @property
  def X_GOOGLE_COM_NegotiationCount24(self):
    return self._GetStats.get('Negotiations24hr', 0)

  @property
  def X_GOOGLE_COM_VendorId(self):
    return self._GetStats.get('VendorId', '')

  @property
  def X_GOOGLE_COM_ProductId(self):
    return self._GetStats.get('ProductId', 0)

  @property
  def X_GOOGLE_COM_MfgYear(self):
    return self._GetStats.get('MfgYear', 1990)

  @property
  def X_GOOGLE_COM_LastUpdateTimestamp(self):
    return tr.cwmpdate.format(float(self._GetStats.get('LastUpdateTime', 0)))


class ServiceMonitoring(BASE135STB.ServiceMonitoring):
  """STBService.{i}.ServiceMonitoring."""

  def __init__(self):
    super(ServiceMonitoring, self).__init__()
    self.Unexport('FetchSamples')
    self.Unexport('ForceSample')
    self.Unexport('ReportEndTime')
    self.Unexport('ReportSamples')
    self.Unexport('ReportStartTime')
    self.Unexport('SampleEnable')
    self.Unexport('SampleInterval')
    self.Unexport('SampleState')
    self.Unexport('TimeReference')
    self.Unexport('EventsPerSampleInterval')
    self.Unexport(objects='GlobalOperation')
    self._MainStreamStats = dict()
    self.MainStreamList = tr.core.AutoDict(
        'MainStreamList', iteritems=self.IterMainStreams,
        getitem=self.GetMainStreamByIndex)

  @property
  def MainStreamNumberOfEntries(self):
    return len(self.MainStreamList)

  def UpdateSvcMonitorStats(self):
    """Retrieve and aggregate stats from all related JSON stats files."""
    streams = dict()
    for wildcard in CONT_MONITOR_FILES:
      for filename in glob.glob(wildcard):
        self.DeserializeStats(filename, streams)

    num_streams = len(streams)
    new_main_stream_stats = dict()
    old_main_stream_stats = self._MainStreamStats

    # Existing stream_ids keep their instance number in self._MainStreamStats
    for instance, old_stream in old_main_stream_stats.items():
      stream_id = old_stream.stream_id
      if stream_id in streams:
        new_main_stream_stats[instance] = streams[stream_id]
        del streams[stream_id]

    # Remaining stream_ids claim an unused instance number in 1..num_streams
    assigned = set(new_main_stream_stats.keys())
    unassigned = set(range(1, num_streams + 1)) - assigned
    for strm in streams.values():
      instance = unassigned.pop()
      new_main_stream_stats[instance] = strm

    self._MainStreamStats = new_main_stream_stats

  def ReadJSONStats(self, fname):
    """Retrieves statistics from the service monitoring JSON file."""
    d = None
    with open(fname) as f:
      d = json.load(f)
    return d

  def DeserializeStats(self, fname, new_streams):
    """Generate stats object from the JSON stats."""
    try:
      d = self.ReadJSONStats(fname)
      streams = d['STBService'][0]['MainStream']
      for i in range(len(streams)):
        stream_id = streams[i]['StreamId']
        strm = new_streams.get(stream_id, MainStream(stream_id))
        strm.UpdateMainstreamStats(streams[i])
        new_streams[stream_id] = strm
    # IOError - Failed to open file or failed to read from file
    # ValueError - JSON file is malformed and cannot be decoded
    # KeyError - Decoded JSON file doesn't contain the required fields.
    except (IOError, ValueError, KeyError) as e:
      print('ServiceMonitoring: Failed to read stats from file {0}, '
            'error = {1}'.format(fname, e))

  def IterMainStreams(self):
    """Retrieves an iterable list of stats."""
    self.UpdateSvcMonitorStats()
    return self._MainStreamStats.items()

  def GetMainStreamByIndex(self, index):
    """Directly access the value corresponding to a given key."""
    self.UpdateSvcMonitorStats()
    return self._MainStreamStats[index]


class MainStream(BASE135STB.ServiceMonitoring.MainStream):
  """STBService.{i}.ServiceMonitoring.MainStream."""

  def __init__(self, stream_id):
    super(MainStream, self).__init__()
    self.Unexport('AVStream')
    self.Unexport('Enable')
    self.Unexport('Gmin')
    self.Unexport('ServiceType')
    self.Unexport('SevereLossMinDistance')
    self.Unexport('SevereLossMinLength')
    self.Unexport('Status')
    self.Unexport('ChannelChangeFailureTimeout')
    self.Unexport('Alias')
    self.Unexport(objects='Sample')
    self.Export(params=['X_GOOGLE-COM_StreamID'])
    self.Total = Total()
    self.stream_id = stream_id

  @property
  def X_GOOGLE_COM_StreamID(self):
    return self.stream_id

  def UpdateMainstreamStats(self, data):
    self.Total.UpdateTotalStats(data)


class Total(BASE135STB.ServiceMonitoring.MainStream.Total):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total."""

  def __init__(self):
    super(Total, self).__init__()
    self.Unexport('Reset')
    self.Unexport('ResetTime')
    self.Unexport('TotalSeconds')
    self.Unexport(objects='AudioDecoderStats')
    self.Unexport(objects='RTPStats')
    self.Unexport(objects='VideoDecoderStats')
    self.Unexport(objects='VideoResponseStats')
    self.DejitteringStats = DejitteringStats()
    self.MPEG2TSStats = MPEG2TSStats()
    self.TCPStats = TCPStats()

  def UpdateTotalStats(self, data):
    if 'DejitteringStats' in data.keys():
      self.DejitteringStats.UpdateDejitteringStats(data['DejitteringStats'])
    if 'MPEG2TSStats' in data.keys():
      self.MPEG2TSStats.UpdateMPEG2TSStats(data['MPEG2TSStats'])
    if 'TCPStats' in data.keys():
      self.TCPStats.UpdateTCPStats(data['TCPStats'])


class DejitteringStats(BASE135STB.ServiceMonitoring.MainStream.Total.
                       DejitteringStats):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total.DejitteringStats."""

  def __init__(self):
    super(DejitteringStats, self).__init__()
    self.Unexport('TotalSeconds')
    self.Export(params=['X_GOOGLE-COM_SessionID'])
    self._empty_buffer_time = 0
    self._overruns = 0
    self._underruns = 0
    self._session_id = 0

  @property
  def EmptyBufferTime(self):
    return self._empty_buffer_time

  @property
  def Overruns(self):
    return self._overruns

  @property
  def Underruns(self):
    return self._underruns

  @property
  def X_GOOGLE_COM_SessionID(self):
    return self._session_id

  def UpdateDejitteringStats(self, djstats):
    if 'EmptyBufferTime' in djstats.keys():
      self._empty_buffer_time = djstats['EmptyBufferTime']
    if 'Overruns' in djstats.keys():
      self._overruns = djstats['Overruns']
    if 'Underruns' in djstats.keys():
      self._underruns = djstats['Underruns']
    if 'SessionId' in djstats.keys():
      self._session_id = djstats['SessionId']


class MPEG2TSStats(BASE135STB.ServiceMonitoring.MainStream.Total.MPEG2TSStats):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total.MPEG2TSStats."""

  def __init__(self):
    super(MPEG2TSStats, self).__init__()
    self.Unexport('PacketDiscontinuityCounterBeforeCA')
    self.Unexport('TSSyncByteErrorCount')
    self.Unexport('TSSyncLossCount')
    self.Unexport('TotalSeconds')
    self._packet_discont_counter = 0
    self._ts_packets_received = 0

  @property
  def PacketDiscontinuityCounter(self):
    return self._packet_discont_counter

  @property
  def TSPacketsReceived(self):
    return self._ts_packets_received

  def UpdateMPEG2TSStats(self, tsstats):
    if 'PacketsDiscontinuityCounter' in tsstats.keys():
      self._packet_discont_counter = tsstats['PacketsDiscontinuityCounter']
    if 'TSPacketsReceived' in tsstats.keys():
      self._ts_packets_received = tsstats['TSPacketsReceived']


class TCPStats(BASE135STB.ServiceMonitoring.MainStream.Total.TCPStats):
  """STBService.{i}.ServiceMonitoring.MainStream.{i}.Total.TCPStats."""

  def __init__(self):
    super(TCPStats, self).__init__()
    self.Unexport('TotalSeconds')
    self._bytes_received = 0
    self._packets_received = 0
    self._packets_retransmitted = 0

  @property
  def BytesReceived(self):
    return self._bytes_received

  @property
  def PacketsReceived(self):
    return self._packets_received

  @property
  def PacketsRetransmitted(self):
    return self._packets_retransmitted

  def UpdateTCPStats(self, tcpstats):
    if 'Bytes Received' in tcpstats.keys():
      self._bytes_received = tcpstats['Bytes Received']
    if 'Packets Received' in tcpstats.keys():
      self._packets_received = tcpstats['Packets Received']
    if 'Packets Retransmitted' in tcpstats.keys():
      self._packets_retransmitted = tcpstats['Packets Retransmitted']


class ProgMetadata(BASEPROGMETADATA.X_CATAWAMPUS_ORG_ProgramMetadata):
  """STBService.{i}.X_CATAWAMPUS_ORG_ProgramMetadata."""

  def __init__(self):
    super(ProgMetadata, self).__init__()
    self.EPG = EPG()


class EPG(BASEPROGMETADATA.X_CATAWAMPUS_ORG_ProgramMetadata.EPG):
  """STBService.{i}.X_CATAWAMPUS_ORG_ProgramMetadata.EPG."""

  def __init__(self):
    super(EPG, self).__init__()

  @property
  @cwmp_session.cache
  def _GetStats(self):
    """Generate stats object from the JSON stats."""
    data = dict()
    for wildcard in EPG_STATS_FILES:
      for filename in glob.glob(wildcard):
        try:
          with open(filename) as f:
            d = json.load(f)
            epgStats = d['EPGStats']

            if 'MulticastPackets' in epgStats.keys():
              data['MulticastPackets'] = epgStats['MulticastPackets']
            if 'EPGErrors' in epgStats.keys():
              data['EPGErrors'] = epgStats['EPGErrors']
            if 'LastReceivedTime' in epgStats.keys():
              data['LastReceivedTime'] = epgStats['LastReceivedTime']
            if'EPGExpireTime' in epgStats.keys():
              data['EPGExpireTime'] = epgStats['EPGExpireTime']

        # IOError - Failed to open file or failed to read from file
        # ValueError - JSON file is malformed and cannot be decoded
        # KeyError - Decoded JSON file doesn't contain the required fields.
        except (IOError, ValueError, KeyError) as e:
          print('EPGStats: Failed to read stats from file {0}, '
                'error = {1}'.format(filename, e))

    return data

  @property
  def MulticastPackets(self):
    return self._GetStats.get('MulticastPackets', 0)

  @property
  def EPGErrors(self):
    return self._GetStats.get('EPGErrors', 0)

  @property
  def LastReceivedTime(self):
    return tr.cwmpdate.format(float(self._GetStats.get('LastReceivedTime', 0)))

  @property
  def EPGExpireTime(self):
    return tr.cwmpdate.format(float(self._GetStats.get('EPGExpireTime', 0)))


def main():
  pass

if __name__ == '__main__':
  main()
