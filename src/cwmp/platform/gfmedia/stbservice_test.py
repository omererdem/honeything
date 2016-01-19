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

# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for stbservice.py implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import unittest

import google3
import stbservice


class STBServiceTest(unittest.TestCase):
  def setUp(self):
    self.CONT_MONITOR_FILES_ALT = ['testdata/stbservice/stats_small.json']
    self.CONT_MONITOR_FILES_P = ['testdata/stbservice/stats_small.json',
                                 'testdata/stbservice/stats_p2.json',
                                 'testdata/stbservice/stats_p1.json',
                                 'testdata/stbservice/notexist.json']
    self.CONT_MONITOR_FILES_P1 = ['testdata/stbservice/stats_p1.json']
    self.STATS_FILES_NOEXST = ['testdata/stbservice/notexist.json']

    self.old_CONT_MONITOR_FILES = stbservice.CONT_MONITOR_FILES
    self.old_EPG_STATS_FILES = stbservice.EPG_STATS_FILES
    self.old_HDMI_DISP_DEVICE_STATS = stbservice.HDMI_DISPLAY_DEVICE_STATS_FILES
    self.old_HDMI_STATS_FILE = stbservice.HDMI_STATS_FILE
    self.old_PROCNETIGMP = stbservice.PROCNETIGMP
    self.old_PROCNETIGMP6 = stbservice.PROCNETIGMP6

    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_full.json']
    stbservice.EPG_STATS_FILES = ['testdata/stbservice/epgstats.json']
    stbservice.HDMI_DISPLAY_DEVICE_STATS_FILES = [
        'testdata/stbservice/hdmi_dispdev_stats*.json',
        'testdata/stbservice/hdmi_dispdev_status*.json']
    stbservice.HDMI_STATS_FILE = 'testdata/stbservice/hdmi_stats.json'
    stbservice.PROCNETIGMP = 'testdata/stbservice/igmp'
    stbservice.PROCNETIGMP6 = 'testdata/stbservice/igmp6'

  def tearDown(self):
    stbservice.CONT_MONITOR_FILES = self.old_CONT_MONITOR_FILES
    stbservice.EPG_STATS_FILES = self.old_EPG_STATS_FILES
    stbservice.HDMI_DISPLAY_DEVICE_STATS_FILES = self.old_HDMI_DISP_DEVICE_STATS
    stbservice.HDMI_STATS_FILE = self.old_HDMI_STATS_FILE
    stbservice.PROCNETIGMP = self.old_PROCNETIGMP
    stbservice.PROCNETIGMP6 = self.old_PROCNETIGMP6

  def testValidateExports(self):
    stb = stbservice.STBService()
    stb.ValidateExports()

  def testClientGroups(self):
    stb = stbservice.STBService()
    igmp = stb.Components.FrontEndList['1'].IP.IGMP
    self.assertEqual(len(igmp.ClientGroupList), 12)
    expected = set(['224.0.0.1', '225.0.1.3', '225.0.1.6', '225.0.1.10',
                    '225.0.1.13', '225.0.1.18', '225.0.1.20', '225.0.1.153',
                    '225.0.1.158', 'ff02::1', 'ff02::1:ff30:66af',
                    'ff02::1:ff30:64af'])
    actual = set()
    for i in range(1, 13):
      actual.add(igmp.ClientGroupList[i].GroupAddress)
    self.assertEqual(expected, actual)

  def testNonexistentStatsFile(self):
    """Test whether the absence of stats file is handled gracefully."""
    stbservice.CONT_MONITOR_FILES = self.STATS_FILES_NOEXST
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 0)

  def testIncorrectStatsFileFormat(self):
    """Test whether a malformed stats file is handled gracefully."""
    # stbservice.PROCNETIGMP is not a JSON file.
    stbservice.CONT_MONITOR_FILES = [stbservice.PROCNETIGMP]
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 0)

  def testIncorrectObjectListIndex(self):
    """Test whether incorrect indexing of the stream object is handled."""
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 8)
    self.assertRaises(KeyError,
                      lambda: stb.ServiceMonitoring.MainStreamList[9])

  def testDynamicUpdate(self):
    """Test whether the object stays consistent when the file is updated."""
    savedfnames = stbservice.CONT_MONITOR_FILES
    stbservice.CONT_MONITOR_FILES = self.CONT_MONITOR_FILES_ALT
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 4)
    for stream in stb.ServiceMonitoring.MainStreamList.values():
      if stream.X_GOOGLE_COM_StreamID == 3:
        self.assertEqual(stream.Total.MPEG2TSStats.TSPacketsReceived, 600)
    self.assertRaises(KeyError,
                      lambda: stb.ServiceMonitoring.MainStreamList[6])
    # Change the underlying json file; The new one has more entries
    stbservice.CONT_MONITOR_FILES = savedfnames
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 8)
    self.assertEqual(stream.Total.MPEG2TSStats.TSPacketsReceived, 600)
    for stream in stb.ServiceMonitoring.MainStreamList.values():
      if stream.X_GOOGLE_COM_StreamID == 3:
        self.assertEqual(stream.Total.MPEG2TSStats.TSPacketsReceived, 600)
      if stream.X_GOOGLE_COM_StreamID == 6:
        self.assertEqual(stream.Total.MPEG2TSStats.TSPacketsReceived, 300)

  def testPartialUpdate(self):
    """Test whether a stats file with a subset of objects are deserialized."""
    stbservice.CONT_MONITOR_FILES = self.CONT_MONITOR_FILES_P1
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 8)
    # Dejittering stats not present in file. Check whether the object is init'ed
    expected_emptybuftime = set([0, 0, 0, 0, 0, 0, 0, 0])
    expected_discont = set([10, 20, 30, 40, 50, 60, 70, 80])
    actual_emptybuftime = set()
    actual_discont = set()
    for v in stb.ServiceMonitoring.MainStreamList.values():
      actual_emptybuftime.add(v.Total.DejitteringStats.EmptyBufferTime)
      actual_discont.add(v.Total.MPEG2TSStats.PacketDiscontinuityCounter)
    self.assertEqual(expected_emptybuftime, actual_emptybuftime)
    self.assertEqual(expected_discont, actual_discont)

  def testAggregateUpdate(self):
    """Test deserialization from multiple source files."""
    stbservice.CONT_MONITOR_FILES = self.CONT_MONITOR_FILES_P
    self.testTSStats()
    self.testDejitteringStats()
    self.testTCPStats()

  def testTSStats(self):
    """Test whether transport stream stats are deserialized."""
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 8)
    expected_discont = set([10, 20, 30, 40, 50, 60, 70, 80])
    expected_pkts = set([100, 200, 300, 400, 500, 600, 700, 800])
    actual_discont = set()
    actual_pkts = set()
    #using iterators to read the stream data. This should reduce the file reads.
    for v in stb.ServiceMonitoring.MainStreamList.values():
      tsstats = v.Total.MPEG2TSStats
      actual_discont.add(tsstats.PacketDiscontinuityCounter)
      actual_pkts.add(tsstats.TSPacketsReceived)
    self.assertEqual(expected_discont, actual_discont)
    self.assertEqual(expected_pkts, actual_pkts)

  def testDejitteringStats(self):
    """Test whether Dejittering stats are deserialized."""
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 8)
    expected_emptybuftime = set([1, 5, 11, 17, 23, 31, 41, 47])
    expected_overruns = set([1, 2, 3, 4, 5, 6, 7, 8])
    expected_underruns = set([18, 17, 16, 15, 14, 13, 12, 11])
    actual_emptybuftime = set()
    actual_underruns = set()
    actual_overruns = set()
    for v in stb.ServiceMonitoring.MainStreamList.values():
      djstats = v.Total.DejitteringStats
      actual_emptybuftime.add(djstats.EmptyBufferTime)
      actual_overruns.add(djstats.Overruns)
      actual_underruns.add(djstats.Underruns)
    self.assertEqual(expected_emptybuftime, actual_emptybuftime)
    self.assertEqual(expected_underruns, actual_underruns)
    self.assertEqual(expected_overruns, actual_overruns)

  def testTCPStats(self):
    """Test whether TCP stats are deserialized."""
    stb = stbservice.STBService()
    self.assertEqual(stb.ServiceMonitoring.MainStreamNumberOfEntries, 8)
    expected_pktsrcvd = set([1000, 2000, 3000, 4000, 5000, 6000, 7000,
                             8000])
    expected_bytesrcvd = set([256000, 512000, 768000, 1024000, 1280000, 1536000,
                              1792000, 2048000])
    expected_pktsretran = set([1, 3, 2, 5, 4, 7, 6, 9])
    actual_pktsrcvd = set()
    actual_bytesrcvd = set()
    actual_pktsretran = set()
    for v in stb.ServiceMonitoring.MainStreamList.values():
      tcpstats = v.Total.TCPStats
      actual_pktsrcvd.add(tcpstats.PacketsReceived)
      actual_bytesrcvd.add(tcpstats.BytesReceived)
      actual_pktsretran.add(tcpstats.PacketsRetransmitted)
    self.assertEqual(expected_pktsrcvd, actual_pktsrcvd)
    self.assertEqual(expected_bytesrcvd, actual_bytesrcvd)
    self.assertEqual(expected_pktsretran, actual_pktsretran)

  def testInstancePersistance(self):
    """Test whether MainStream instance numbers are persistent."""
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_strm1.json']
    stb = stbservice.STBService()
    m = stb.ServiceMonitoring
    self.assertEqual(m.MainStreamNumberOfEntries, 1)
    self.assertEqual(m.MainStreamList[1].X_GOOGLE_COM_StreamID, 1)
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_strm12.json']
    self.assertEqual(m.MainStreamNumberOfEntries, 2)
    self.assertEqual(m.MainStreamList[1].X_GOOGLE_COM_StreamID, 1)
    self.assertEqual(m.MainStreamList[2].X_GOOGLE_COM_StreamID, 2)
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_strm123.json']
    self.assertEqual(m.MainStreamNumberOfEntries, 3)
    self.assertEqual(m.MainStreamList[1].X_GOOGLE_COM_StreamID, 1)
    self.assertEqual(m.MainStreamList[2].X_GOOGLE_COM_StreamID, 2)
    self.assertEqual(m.MainStreamList[3].X_GOOGLE_COM_StreamID, 3)
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_strm2.json']
    self.assertEqual(m.MainStreamNumberOfEntries, 1)
    self.assertEqual(m.MainStreamList[2].X_GOOGLE_COM_StreamID, 2)
    stbservice.CONT_MONITOR_FILES = ['testdata/stbservice/stats_strm23.json']
    self.assertEqual(m.MainStreamNumberOfEntries, 2)
    self.assertEqual(m.MainStreamList[1].X_GOOGLE_COM_StreamID, 3)
    self.assertEqual(m.MainStreamList[2].X_GOOGLE_COM_StreamID, 2)
    stb.ValidateExports()

  def testNonexistentHDMIStatsFile(self):
    """Test whether the absence of HDMI stats file is handled gracefully."""
    stbservice.HDMI_STATS_FILE = self.STATS_FILES_NOEXST[0]
    stbservice.HDMI_DISPLAY_DEVICE_STATS_FILES = self.STATS_FILES_NOEXST
    stb = stbservice.STBService()
    self.assertEqual(stb.Components.HDMINumberOfEntries, 1)
    for v in stb.Components.HDMIList.values():
      self.assertEqual(v.ResolutionMode, 'Auto')
      self.assertEqual(v.ResolutionValue, '')
      self.assertEqual(v.DisplayDevice.Status, 'None')
      self.assertEqual(v.DisplayDevice.Name, '')
      self.assertEqual(v.DisplayDevice.EEDID, '')
      self.assertEqual(len(v.DisplayDevice.SupportedResolutions), 0)
      self.assertEqual(v.DisplayDevice.PreferredResolution, '')
      self.assertEqual(v.DisplayDevice.VideoLatency, 0)
      self.assertEqual(v.DisplayDevice.AutoLipSyncSupport, False)
      self.assertEqual(v.DisplayDevice.HDMI3DPresent, False)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount4, 0)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount24, 0)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_VendorId, '')
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_ProductId, 0)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_MfgYear, 1990)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_LastUpdateTimestamp,
                       '0001-01-01T00:00:00Z')

  def testHDMIStatsAll(self):
    """Test deserialization of all HDMI stats parameters."""
    stb = stbservice.STBService()
    self.assertEqual(stb.Components.HDMINumberOfEntries, 1)
    for v in stb.Components.HDMIList.values():
      self.assertEqual(v.ResolutionMode, 'Auto')
      self.assertEqual(v.ResolutionValue, '640x480 @ 51Hz')
      self.assertEqual(v.DisplayDevice.Status, 'Present')
      self.assertEqual(v.DisplayDevice.Name, 'X213W')
      self.assertEqual(v.DisplayDevice.EEDID, ('00ffffffffffff000472330088b4808'
                                               '008120103802f1e78eade95a3544c99'
                                               '260f5054bfef90a940714f814001019'
                                               '500950f9040010121399030621a2740'
                                               '68b03600da2811000019000000fd003'
                                               '84d1f5411000a202020202020000000'
                                               'ff004c43473043303233343031300a0'
                                               '00000fc0058323133570a2020202020'
                                               '202000d9'))
      self.assertEqual(v.DisplayDevice.SupportedResolutions, ('640x480 @ 51Hz, '
                                                              '640x480 @ 52Hz, '
                                                              '640x480 @ 55Hz'))
      self.assertEqual(v.DisplayDevice.PreferredResolution, '640x480 @ 51Hz')
      self.assertEqual(v.DisplayDevice.VideoLatency, 0)
      self.assertEqual(v.DisplayDevice.AutoLipSyncSupport, False)
      self.assertEqual(v.DisplayDevice.HDMI3DPresent, False)

      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_EDIDExtensions,
                       v.DisplayDevice.EEDID + ', ' + v.DisplayDevice.EEDID)

      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount4, 3)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount24, 9)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_VendorId, 'ACR')
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_ProductId, 51)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_MfgYear, 2008)

  def testIncorrectHDMIStatsFile(self):
    """Test deserialization when a subset of stats files are invalid."""
    stbservice.HDMI_STATS_FILE = stbservice.PROCNETIGMP
    stb = stbservice.STBService()
    self.assertEqual(stb.Components.HDMINumberOfEntries, 1)
    for v in stb.Components.HDMIList.values():
      self.assertEqual(v.ResolutionMode, 'Auto')
      self.assertEqual(v.ResolutionValue, '')
      self.assertEqual(v.DisplayDevice.Name, 'X213W')

  def testPartialHDMIStatsFiles(self):
    """Test deserialization when a subset of files are not present."""
    stbservice.HDMI_DISPLAY_DEVICE_STATS_FILES = [
        'testdata/stbservice/hdmi_dispdev_status.json']
    stb = stbservice.STBService()
    self.assertEqual(stb.Components.HDMINumberOfEntries, 1)
    for v in stb.Components.HDMIList.values():
      self.assertEqual(v.ResolutionMode, 'Auto')
      self.assertEqual(v.ResolutionValue, '640x480 @ 51Hz')
      self.assertEqual(v.DisplayDevice.Status, 'Present')
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount4, 3)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_NegotiationCount24, 9)
      self.assertEqual(v.DisplayDevice.Name, '')
      self.assertEqual(v.DisplayDevice.EEDID, '')
      self.assertEqual(len(v.DisplayDevice.SupportedResolutions), 0)
      self.assertEqual(v.DisplayDevice.PreferredResolution, '')
      self.assertEqual(v.DisplayDevice.VideoLatency, 0)
      self.assertEqual(v.DisplayDevice.AutoLipSyncSupport, False)
      self.assertEqual(v.DisplayDevice.HDMI3DPresent, False)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_VendorId, '')
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_ProductId, 0)
      self.assertEqual(v.DisplayDevice.X_GOOGLE_COM_MfgYear, 1990)

  def testEPGStatsNoFile(self):
    """Test whether EPG stats are deserialized properly when not file backed."""
    stbservice.EPG_STATS_FILES = self.STATS_FILES_NOEXST
    stb = stbservice.STBService()
    stb.X_CATAWAMPUS_ORG_ProgramMetadata.ValidateExports()
    epgStats = stb.X_CATAWAMPUS_ORG_ProgramMetadata.EPG
    self.assertEqual(epgStats.MulticastPackets, 0)
    self.assertEqual(epgStats.EPGErrors, 0)
    self.assertEqual(epgStats.LastReceivedTime, '0001-01-01T00:00:00Z')
    self.assertEqual(epgStats.EPGExpireTime, '0001-01-01T00:00:00Z')

  def testEPGStatsIncorrectFileFormat(self):
    """Test whether EPG stats are handled properly for a bad file."""
    stbservice.EPG_STATS_FILES = [stbservice.PROCNETIGMP]
    stb = stbservice.STBService()
    stb.X_CATAWAMPUS_ORG_ProgramMetadata.ValidateExports()
    epgStats = stb.X_CATAWAMPUS_ORG_ProgramMetadata.EPG
    self.assertEqual(epgStats.MulticastPackets, 0)
    self.assertEqual(epgStats.EPGErrors, 0)
    self.assertEqual(epgStats.LastReceivedTime, '0001-01-01T00:00:00Z')
    self.assertEqual(epgStats.EPGExpireTime, '0001-01-01T00:00:00Z')

  def testEPGStatsAll(self):
    """Test whether EPG stats are deserialized properly."""
    stb = stbservice.STBService()
    stb.X_CATAWAMPUS_ORG_ProgramMetadata.ValidateExports()
    epgStats = stb.X_CATAWAMPUS_ORG_ProgramMetadata.EPG
    self.assertEqual(epgStats.MulticastPackets, 1002)
    self.assertEqual(epgStats.EPGErrors, 2)
    self.assertEqual(epgStats.LastReceivedTime, '2012-07-25T01:50:37Z')
    self.assertEqual(epgStats.EPGExpireTime, '2012-07-30T01:50:37Z')


if __name__ == '__main__':
  unittest.main()
