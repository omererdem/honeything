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

"""Device Models for a simulated CPE."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import os
import sys
import google3
import dm.device_info
import dm.igd_time
import dm.periodic_statistics
import dm.storage
import platform_config
import tornado.ioloop
import tr.core
import tr.download
import tr.tr181_v2_2 as tr181

from src.config.ConfigReader import ConfigReader
from src.logger.HoneythingLogging import HTLogging

ht = HTLogging()

FAKECPEINSTANCE = None
INTERNAL_ERROR = 9002
BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice


class PlatformConfig(platform_config.PlatformConfigMeta):
  """PlatformConfig for FakeCPE."""

  cfg = ConfigReader()

  def __init__(self, ioloop=None):
    platform_config.PlatformConfigMeta.__init__(self)

  def ConfigDir(self):
    #return '/tmp/catawampus.%s/config/' % FakeCPEInstance()
    return PlatformConfig.cfg.getConfig('cwmp', 'cwmp_dir') + '/cpe.%s/config/' % FakeCPEInstance()

  def DownloadDir(self):
    #return '/tmp/catawampus.%s/download/' % FakeCPEInstance()
    return PlatformConfig.cfg.getConfig('cwmp', 'cwmp_dir') + '/cpe.%s/download/' % FakeCPEInstance()

  def GetAcsUrl(self):
    """FakeCPE requires a --acs_url parameter, there is no platform handling."""
    return None

  def SetAcsUrl(self, url):
    raise AttributeError('URL is read-only')

  def AcsAccessAttempt(self, url):
    pass

  def AcsAccessSuccess(self, url):
    pass


class InstallerFakeCPE(tr.download.Installer):
  """Fake Installer to install fake images on a fake CPE."""

  def __init__(self, filename, ioloop=None):
    tr.download.Installer.__init__(self)
    self.filename = filename
    self._install_cb = None
    self._ioloop = ioloop or tornado.ioloop.IOLoop.instance()

  def _call_callback(self, faultcode, faultstring):
    if self._install_cb:
      self._install_cb(faultcode, faultstring, must_reboot=True)

  def install(self, file_type, target_filename, callback):
    ftype = file_type.split()
    #if ftype and ftype[0] != '1':
    #  self._call_callback(INTERNAL_ERROR,
    #                      'Unsupported file_type {0}'.format(type[0]))
    #  return False
    self._install_cb = callback
    os.rename(self.filename, 'download.tgz')
    self._call_callback(0, '')
    return True

  def reboot(self):
    #sys.exit(32)
    ht.logger.info('Download completed and reboot function called (fake reboot)')



def FakeCPEInstance():
  cfg = ConfigReader()
  global FAKECPEINSTANCE
  if FAKECPEINSTANCE is None:
    FAKECPEINSTANCE = os.getenv('FAKECPEINSTANCE', cfg.getConfig("cpe", "serial_number"))
  return FAKECPEINSTANCE


class DeviceIdFakeCPE(dm.device_info.DeviceIdMeta):
  """Parameters for the DeviceInfo object for a FakeCPE platform."""

  cfg = ConfigReader()

  @property
  def Manufacturer(self):
    #return 'Catawampus'
    return DeviceIdFakeCPE.cfg.getConfig("cpe", "manufacturer")

  @property
  def ManufacturerOUI(self):
    #return '001A11'
    return DeviceIdFakeCPE.cfg.getConfig("cpe", "manufacturer_oui")

  @property
  def ModelName(self):
    #return 'FakeCPE'
    return DeviceIdFakeCPE.cfg.getConfig("cpe", "model_name")

  @property
  def Description(self):
    #return 'Simulated CPE device'
    return DeviceIdFakeCPE.cfg.getConfig("cpe", "description")

  @property
  def SerialNumber(self):
    return str(FakeCPEInstance())

  @property
  def HardwareVersion(self):
    #return '0'
    return DeviceIdFakeCPE.cfg.getConfig("cpe", "hardware_version")

  @property
  def AdditionalHardwareVersion(self):
    return '0'

  @property
  def SoftwareVersion(self):
    try:
      #with open('platform/fakecpe/version', 'r') as f:
      #  return f.readline().strip()
      return DeviceIdFakeCPE.cfg.getConfig("cpe", "software_version")
    except IOError:
      return 'unknown_version'

  @property
  def AdditionalSoftwareVersion(self):
    return '0'

  @property
  def ProductClass(self):
    #return 'Simulation'
    return DeviceIdFakeCPE.cfg.getConfig("cpe", "product_class")

  @property
  def ModemFirmwareVersion(self):
    #return '0'
    return DeviceIdFakeCPE.cfg.getConfig("cpe", "firmware_version")


class ServicesFakeCPE(tr181.Device_v2_2.Device.Services):
  def __init__(self):
    tr181.Device_v2_2.Device.Services.__init__(self)
    self.Export(objects=['StorageServices'])
    self.StorageServices = dm.storage.StorageServiceLinux26()


class DeviceFakeCPE(tr181.Device_v2_2.Device):
  """Device implementation for a simulated CPE device."""

  def __init__(self, device_id, periodic_stats):
    super(DeviceFakeCPE, self).__init__()
    self.Unexport(objects='ATM')
    self.Unexport(objects='Bridging')
    self.Unexport(objects='CaptivePortal')
    self.Export(objects=['DeviceInfo'])
    self.Unexport(objects='DHCPv4')
    self.Unexport(objects='DHCPv6')
    self.Unexport(objects='DNS')
    self.Unexport(objects='DSL')
    self.Unexport(objects='DSLite')
    self.Unexport(objects='Ethernet')
    self.Unexport(objects='Firewall')
    self.Unexport(objects='GatewayInfo')
    self.Unexport(objects='HPNA')
    self.Unexport(objects='HomePlug')
    self.Unexport(objects='Hosts')
    self.Unexport(objects='IEEE8021x')
    self.Unexport(objects='IP')
    self.Unexport(objects='IPv6rd')
    self.Unexport(objects='LANConfigSecurity')
    self.Unexport(objects='MoCA')
    self.Unexport(objects='NAT')
    self.Unexport(objects='NeighborDiscovery')
    self.Unexport(objects='PPP')
    self.Unexport(objects='PTM')
    self.Unexport(objects='QoS')
    self.Unexport(objects='RouterAdvertisement')
    self.Unexport(objects='Routing')
    self.Unexport(objects='SmartCardReaders')
    self.Unexport(objects='UPA')
    self.Unexport(objects='USB')
    self.Unexport(objects='Users')
    self.Unexport(objects='WiFi')

    self.DeviceInfo = dm.device_info.DeviceInfo181Linux26(device_id)
    self.ManagementServer = tr.core.TODO()  # Higher layer code splices this in
    self.Services = ServicesFakeCPE()

    self.InterfaceStackNumberOfEntries = 0
    self.InterfaceStackList = {}

    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats


class InternetGatewayDeviceFakeCPE(BASE98IGD):
  """Implements tr-98 InternetGatewayDevice."""

  def __init__(self, device_id, periodic_stats):
    super(InternetGatewayDeviceFakeCPE, self).__init__()
    self.Unexport(objects='CaptivePortal')
    self.Unexport(objects='DeviceConfig')
    self.Unexport(params='DeviceSummary')
    self.Unexport(objects='DownloadDiagnostics')
    self.Unexport(objects='IPPingDiagnostics')
    self.Unexport(objects='LANConfigSecurity')
    self.Unexport(lists='LANDevice')
    self.Unexport(objects='LANInterfaces')
    self.Unexport(objects='Layer2Bridging')
    self.Unexport(objects='Layer3Forwarding')
    self.ManagementServer = tr.core.TODO()  # higher level code splices this in
    self.Unexport(objects='QueueManagement')
    self.Unexport(objects='Services')
    self.Unexport(objects='TraceRouteDiagnostics')
    self.Unexport(objects='UploadDiagnostics')
    self.Unexport(objects='UserInterface')
    self.Unexport(lists='WANDevice')

    self.DeviceInfo = dm.device_info.DeviceInfo98Linux26(device_id)
    tzfile = '/tmp/catawampus.%s/TZ' % FakeCPEInstance()
    self.Time = dm.igd_time.TimeTZ(tzfile=tzfile)
    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats

  @property
  def LANDeviceNumberOfEntries(self):
    return 0

  @property
  def WANDeviceNumberOfEntries(self):
    return 0


def PlatformInit(name, device_model_root):
  """Create platform-specific device models and initialize platform."""
  tr.download.INSTALLER = InstallerFakeCPE
  params = list()
  objects = list()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  devid = DeviceIdFakeCPE()
  device_model_root.Device = DeviceFakeCPE(devid, periodic_stats)
  objects.append('Device')
  device_model_root.InternetGatewayDevice = InternetGatewayDeviceFakeCPE(
      devid, periodic_stats)
  objects.append('InternetGatewayDevice')
  return (params, objects)


def main():
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  devid = DeviceIdFakeCPE()
  device = DeviceFakeCPE(devid, periodic_stats)
  igd = InternetGatewayDeviceFakeCPE(devid, periodic_stats)
  tr.core.Dump(device)
  tr.core.Dump(igd)
  device.ValidateExports()
  igd.ValidateExports()
  print 'done'

if __name__ == '__main__':
  main()
