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

"""tr-181 Device implementations for supported platforms."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime
import fcntl
import os
import random
import subprocess
import traceback

import google3

import dm.brcmmoca
import dm.brcmwifi
import dm.device_info
import dm.ethernet
import dm.igd_time
import dm.periodic_statistics
import dm.storage
import dm.temperature
import platform_config
import pynetlinux
import tornado.ioloop
import tr.core
import tr.download
import tr.tr098_v1_2
import tr.tr181_v2_2 as tr181
import tr.x_catawampus_tr181_2_0

import gfibertv
import gvsb
import stbservice


BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
CATA181DI = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.DeviceInfo
PYNETIFCONF = pynetlinux.ifconfig.Interface

# tr-69 error codes
INTERNAL_ERROR = 9002

# Unit tests can override these with fake data
ACSCONNECTED = '/tmp/gpio/ledcontrol/acsconnected'
ACSTIMEOUTMIN = 2*60*60
ACSTIMEOUTMAX = 4*60*60
CONFIGDIR = '/config/tr69'
DOWNLOADDIR = '/tmp'
GINSTALL = '/bin/ginstall.py'
HNVRAM = '/usr/bin/hnvram'
LEDSTATUS = '/tmp/gpio/ledstate'
NAND_MB = '/proc/sys/dev/repartition/nand_size_mb'
PROC_CPUINFO = '/proc/cpuinfo'
REBOOT = '/bin/tr69_reboot'
REPOMANIFEST = '/etc/repo-buildroot-manifest'
SET_ACS = 'set-acs'
VERSIONFILE = '/etc/version'


class PlatformConfig(platform_config.PlatformConfigMeta):
  """PlatformConfig for GFMedia devices."""

  def __init__(self, ioloop=None):
    platform_config.PlatformConfigMeta.__init__(self)
    self._ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.acs_timeout = None
    self.acs_timeout_interval = random.randrange(ACSTIMEOUTMIN, ACSTIMEOUTMAX)
    self.acs_timeout_url = None

  def ConfigDir(self):
    return CONFIGDIR

  def DownloadDir(self):
    return DOWNLOADDIR

  def GetAcsUrl(self):
    setacs = subprocess.Popen([SET_ACS, 'print'], stdout=subprocess.PIPE)
    out, _ = setacs.communicate(None)
    return out if setacs.returncode == 0 else ''

  def SetAcsUrl(self, url):
    set_acs_url = url if url else 'clear'
    rc = subprocess.call(args=[SET_ACS, 'cwmp', set_acs_url.strip()])
    if rc != 0:
      raise AttributeError('set-acs failed')

  def _AcsAccessClearTimeout(self):
    if self.acs_timeout:
      self._ioloop.remove_timeout(self.acs_timeout)
      self.acs_timeout = None

  def _AcsAccessTimeout(self):
    """Timeout for AcsAccess.

    There has been no successful connection to ACS in self.acs_timeout_interval
    seconds.
    """
    try:
      os.remove(ACSCONNECTED)
    except OSError as e:
      if e.errno != errno.ENOENT:
        raise
      pass  # No such file == harmless

    try:
      rc = subprocess.call(args=[SET_ACS, 'timeout', self.acs_timeout_url.strip()])
    except OSError:
      rc = -1

    if rc != 0:
      # Log the failure
      print '%s timeout %s failed %d' % (SET_ACS, self.acs_timeout_url, rc)

  def AcsAccessAttempt(self, url):
    """Called when a connection to the ACS is attempted."""
    if url != self.acs_timeout_url:
      self._AcsAccessClearTimeout()  # new ACS, restart timer
      self.acs_timeout_url = url
    if not self.acs_timeout:
      self.acs_timeout = self._ioloop.add_timeout(
          datetime.timedelta(seconds=self.acs_timeout_interval),
          self._AcsAccessTimeout)

  def AcsAccessSuccess(self, url):
    """Called when a session with the ACS successfully concludes."""
    self._AcsAccessClearTimeout()
    # We only *need* to create a 0 byte file, but write URL for debugging
    with open(ACSCONNECTED, 'w') as f:
      f.write(url)


class DeviceId(dm.device_info.DeviceIdMeta):
  """Fetch the DeviceInfo parameters from NVRAM."""

  def _GetOneLine(self, filename, default):
    try:
      with open(filename, 'r') as f:
        return f.readline().strip()
    except:
      return default

  def _GetNvramParam(self, param, default=''):
    """Return a parameter from NVRAM, like the serial number.

    Args:
      param: string name of the parameter to fetch. This must match the
        predefined names supported by /bin/hnvram
      default: value to return if the parameter is not present in NVRAM.

    Returns:
      A string value of the contents.
    """
    cmd = [HNVRAM, '-r', param]
    devnull = open('/dev/null', 'w')
    try:
      hnvram = subprocess.Popen(cmd, stdin=devnull, stderr=devnull,
                                stdout=subprocess.PIPE)
      out, _ = hnvram.communicate()
      if hnvram.returncode != 0:
        # Treat failure to run hnvram same as not having the field populated
        out = ''
    except OSError:
      out = ''
    outlist = out.strip().split('=')

    # HNVRAM does not distinguish between "value not present" and
    # "value present, and is empty." Treat empty values as invalid.
    if len(outlist) > 1 and outlist[1].strip():
      return outlist[1].strip()
    else:
      return default

  @property
  def Manufacturer(self):
    return 'Google Fiber'

  @property
  def ManufacturerOUI(self):
    return 'F88FCA'

  @property
  def ModelName(self):
    return self._GetNvramParam('PLATFORM_NAME', default='UnknownModel')

  @property
  def Description(self):
    return 'Set top box for Google Fiber network'

  @property
  def SerialNumber(self):
    serial = self._GetNvramParam('1ST_SERIAL_NUMBER', default=None)
    if serial is None:
      serial = self._GetNvramParam('SERIAL_NO', default='000000000000')
    return serial

  @property
  def HardwareVersion(self):
    """Return NVRAM HW_REV, inferring one if not present."""
    hw_rev = self._GetNvramParam('HW_REV', default=None)
    if hw_rev:
      return hw_rev

    # initial builds with no HW_REV; infer a rev.
    cpu = open(PROC_CPUINFO, 'r').read()
    if cpu.find('BCM7425B0') > 0:
      return '0'
    if cpu.find('BCM7425B2') > 0:
      # B2 chip with 4 Gig MLC flash == rev1. 1 Gig SLC flash == rev2.
      try:
        siz = int(open(NAND_MB, 'r').read())
      except OSError:
        return '?'
      if siz == 4096:
        return '1'
      if siz == 1024:
        return '2'
    return '?'

  @property
  def AdditionalHardwareVersion(self):
    return self._GetNvramParam('GPN', default='')

  @property
  def SoftwareVersion(self):
    return self._GetOneLine(VERSIONFILE, '0')

  @property
  def AdditionalSoftwareVersion(self):
    return self._GetOneLine(REPOMANIFEST, '')

  @property
  def ProductClass(self):
    return self._GetNvramParam('PLATFORM_NAME', default='UnknownModel')

  @property
  def ModemFirmwareVersion(self):
    return '0'


class Installer(tr.download.Installer):
  """Installer class used by tr/download.py."""

  def __init__(self, filename, ioloop=None):
    tr.download.Installer.__init__(self)
    self.filename = filename
    self._install_cb = None
    self._ioloop = ioloop or tornado.ioloop.IOLoop.instance()

  def _call_callback(self, faultcode, faultstring):
    if self._install_cb:
      self._install_cb(faultcode, faultstring, must_reboot=True)

  def install(self, file_type, target_filename, callback):
    """Install self.filename to disk, then call callback."""
    print 'Installing: %r %r' % (file_type, target_filename)
    ftype = file_type.split()
    if ftype and ftype[0] != '1':
      self._call_callback(INTERNAL_ERROR,
                          'Unsupported file_type {0}'.format(ftype[0]))
      return False
    self._install_cb = callback

    if not os.path.exists(self.filename):
      self._call_callback(INTERNAL_ERROR,
                          'Installer: file %r does not exist.' % self.filename)
      return False

    cmd = [GINSTALL, '--tar={0}'.format(self.filename), '--partition=other']
    try:
      self._ginstall = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    except OSError:
      self._call_callback(INTERNAL_ERROR, 'Unable to start installer process')
      return False

    fd = self._ginstall.stdout.fileno()
    fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
    self._ioloop.add_handler(fd, self.on_stdout, self._ioloop.READ)
    return True

  def reboot(self):
    cmd = [REBOOT]
    subprocess.call(cmd)

  def on_stdout(self, fd, events):
    """Called whenever the ginstall process prints to stdout."""
    # drain the pipe
    inp = ''
    try:
      inp = os.read(fd, 4096)
    except OSError:   # returns EWOULDBLOCK
      pass
    if inp and inp.strip() != '.':
      print 'ginstall: %s' % inp.strip()
    if self._ginstall.poll() >= 0:
      self._ioloop.remove_handler(self._ginstall.stdout.fileno())
      if self._ginstall.returncode == 0:
        self._call_callback(0, '')
      else:
        print 'ginstall: exit code %d' % self._ginstall.poll()
        self._call_callback(INTERNAL_ERROR, 'Unable to install image.')


class Services(tr181.Device_v2_2.Device.Services):
  """Implements tr-181 Device.Services."""

  def __init__(self):
    tr181.Device_v2_2.Device.Services.__init__(self)
    self.Export(objects=['StorageServices'])
    self.StorageServices = dm.storage.StorageServiceLinux26()
    self._AddStorageDevices()
    self.Export(lists=['STBService'])
    self.Export(['STBServiceNumberOfEntries'])
    self.STBServiceList = {'1': stbservice.STBService()}

  @property
  def STBServiceNumberOfEntries(self):
    return len(self.STBServiceList)

  def _AddStorageDevices(self):
    num = 0
    for drive in ['sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf']:
      try:
        if os.stat('/sys/block/' + drive):
          phys = dm.storage.PhysicalMediumDiskLinux26(drive, 'SATA/300')
          self.StorageServices.PhysicalMediumList[str(num)] = phys
          num += 1
      except OSError:
        pass

    num = 0
    for i in range(32):
      ubiname = 'ubi' + str(i)
      try:
        if os.stat('/sys/class/ubi/' + ubiname):
          ubi = dm.storage.FlashMediumUbiLinux26(ubiname)
          self.StorageServices.X_CATAWAMPUS_ORG_FlashMediaList[str(num)] = ubi
          num += 1
      except OSError:
        pass


class Ethernet(tr181.Device_v2_2.Device.Ethernet):
  """Implementation of tr-181 Device.Ethernet for GFMedia platforms."""

  def __init__(self):
    tr181.Device_v2_2.Device.Ethernet.__init__(self)
    self.InterfaceList = {'1': dm.ethernet.EthernetInterfaceLinux26('eth0')}
    self.VLANTerminationList = {}
    self.LinkList = {}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)

  @property
  def VLANTerminationNumberOfEntries(self):
    return len(self.VLANTerminationList)

  @property
  def LinkNumberOfEntries(self):
    return len(self.LinkList)


class Moca(tr181.Device_v2_2.Device.MoCA):
  """Implementation of tr-181 Device.MoCA for GFMedia platforms."""

  def __init__(self):
    tr181.Device_v2_2.Device.MoCA.__init__(self)
    self.InterfaceList = {'1': dm.brcmmoca.BrcmMocaInterface('eth1')}

  @property
  def InterfaceNumberOfEntries(self):
    return len(self.InterfaceList)


class FanReadGpio(CATA181DI.TemperatureStatus.X_CATAWAMPUS_ORG_Fan):
  """Implementation of Fan object, reading rev/sec from a file."""

  def __init__(self, name='Fan', speed_filename='/tmp/gpio/fanspeed',
                  percent_filename='/tmp/gpio/fanpercent'):
    super(FanReadGpio, self).__init__()
    self.Unexport(params='DesiredRPM')
    self._name = name
    self._speed_filename = speed_filename
    self._percent_filename = percent_filename

  @property
  def Name(self):
    return self._name

  @property
  def RPM(self):
    try:
      f = open(self._speed_filename, 'r')
    except IOError as e:
      print 'Fan speed file %r: %s' % (self._speed_filename, e)
      return -1
    try:
      rps2 = int(f.read())
      return rps2 * 30
    except ValueError as e:
      print 'FanReadGpio RPM %r: %s' % (self._speed_filename, e)
      return -1

  @property
  def DesiredPercentage(self):
    try:
      f = open(self._percent_filename, 'r')
    except IOError as e:
      print 'Fan percent file %r: %s' % (self._percent_filename, e)
      return -1
    try:
      return int(f.read())
    except ValueError as e:
      print 'FanReadGpio DesiredPercentage %r: %s' % (self._percent_filename, e)
      return -1



class Device(tr181.Device_v2_2.Device):
  """tr-181 Device implementation for Google Fiber media platforms."""

  def __init__(self, device_id, periodic_stats):
    super(Device, self).__init__()
    self.Unexport(objects='ATM')
    self.Unexport(objects='Bridging')
    self.Unexport(objects='CaptivePortal')
    self.Export(objects=['DeviceInfo'])
    self.Unexport(objects='DHCPv4')
    self.Unexport(objects='DHCPv6')
    self.Unexport(objects='DNS')
    self.Unexport(objects='DSL')
    self.Unexport(objects='DSLite')
    self.Unexport(objects='Firewall')
    self.Unexport(objects='GatewayInfo')
    self.Unexport(objects='HPNA')
    self.Unexport(objects='HomePlug')
    self.Unexport(objects='Hosts')
    self.Unexport(objects='IEEE8021x')
    self.Unexport(objects='IP')
    self.Unexport(objects='IPv6rd')
    self.Unexport(objects='LANConfigSecurity')
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
    led = dm.device_info.LedStatusReadFromFile('LED', LEDSTATUS)
    self.DeviceInfo.AddLedStatus(led)
    self.Ethernet = Ethernet()
    self.ManagementServer = tr.core.TODO()  # higher level code splices this in
    self.MoCA = Moca()
    self.Services = Services()
    self.InterfaceStackList = {}
    self.InterfaceStackNumberOfEntries = 0
    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats

    # GFHD100 & GFMS100 both monitor CPU temperature.
    # GFMS100 also monitors hard drive temperature.
    ts = self.DeviceInfo.TemperatureStatus
    ts.AddSensor(name='CPU temperature',
                 sensor=dm.temperature.SensorReadFromFile(
                     '/tmp/gpio/cpu_temperature'))
    for drive in ['sda', 'sdb', 'sdc', 'sdd', 'sde', 'sdf']:
      try:
        if os.stat('/sys/block/' + drive):
          ts.AddSensor(name='Hard drive temperature ' + drive,
                       sensor=dm.temperature.SensorHdparm(drive))
      except OSError:
        pass

    ts.AddFan(FanReadGpio())


class LANDevice(BASE98IGD.LANDevice):
  """tr-98 InternetGatewayDevice for Google Fiber media platforms."""

  def __init__(self):
    super(LANDevice, self).__init__()
    self.Unexport('Alias')
    self.Unexport(objects='Hosts')
    self.Unexport(lists='LANEthernetInterfaceConfig')
    self.Unexport(objects='LANHostConfigManagement')
    self.Unexport(lists='LANUSBInterfaceConfig')
    self.LANEthernetInterfaceNumberOfEntries = 0
    self.LANUSBInterfaceNumberOfEntries = 0
    self.WLANConfigurationList = {}
    if self._has_wifi():
      wifi = dm.brcmwifi.BrcmWifiWlanConfiguration('eth2')
      self.WLANConfigurationList = {'1': wifi}

  def _has_wifi(self):
    try:
      PYNETIFCONF('eth2').get_index()
      return True
    except IOError:
      return False

  @property
  def LANWLANConfigurationNumberOfEntries(self):
    return len(self.WLANConfigurationList)


class InternetGatewayDevice(BASE98IGD):
  """Implements tr-98 InternetGatewayDevice."""

  def __init__(self, device_id, periodic_stats):
    super(InternetGatewayDevice, self).__init__()
    self.Unexport(objects='CaptivePortal')
    self.Unexport(objects='DeviceConfig')
    self.Unexport(params='DeviceSummary')
    self.Unexport(objects='DownloadDiagnostics')
    self.Unexport(objects='IPPingDiagnostics')
    self.Unexport(objects='LANConfigSecurity')
    self.LANDeviceList = {'1': LANDevice()}
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
    self.Time = dm.igd_time.TimeTZ()
    self.Export(objects=['PeriodicStatistics'])
    self.PeriodicStatistics = periodic_stats

  @property
  def LANDeviceNumberOfEntries(self):
    return len(self.LANDeviceList)

  @property
  def WANDeviceNumberOfEntries(self):
    return 0


def PlatformInit(name, device_model_root):
  """Create platform-specific device models and initialize platform."""
  tr.download.INSTALLER = Installer
  params = []
  objects = []
  dev_id = DeviceId()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  device_model_root.Device = Device(dev_id, periodic_stats)
  device_model_root.InternetGatewayDevice = InternetGatewayDevice(
      dev_id, periodic_stats)
  device_model_root.X_GOOGLE_COM_GVSB = gvsb.Gvsb()
  tvrpc = gfibertv.GFiberTv('http://localhost:51834/xmlrpc')
  device_model_root.X_GOOGLE_COM_GFIBERTV = tvrpc
  objects.append('Device')
  objects.append('InternetGatewayDevice')
  objects.append('X_GOOGLE-COM_GVSB')
  objects.append('X_GOOGLE-COM_GFIBERTV')
  return (params, objects)


def main():
  dev_id = DeviceId()
  periodic_stats = dm.periodic_statistics.PeriodicStatistics()
  root = Device(dev_id, periodic_stats)
  root.ValidateExports()
  tr.core.Dump(root)

if __name__ == '__main__':
  main()
