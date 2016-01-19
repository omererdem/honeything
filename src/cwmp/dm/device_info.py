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

"""Implementation of tr-181 Device.DeviceInfo object.

Handles the Device.DeviceInfo portion of TR-181, as described
by http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import abc
import glob
import os
import tornado.ioloop
import temperature
import tr.core
import tr.tr098_v1_4
import tr.tr181_v2_2

BASE98IGD = tr.tr098_v1_4.InternetGatewayDevice_v1_10.InternetGatewayDevice
BASE181DEVICE = tr.tr181_v2_2.Device_v2_2
CATA181DEVICE = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0

# Unit tests can override these with fake data
PERIODICCALL = tornado.ioloop.PeriodicCallback
PROC_MEMINFO = '/proc/meminfo'
PROC_NET_DEV = '/proc/net/dev'
PROC_UPTIME = '/proc/uptime'
PROC_STAT = '/proc/stat'
SLASH_PROC = '/proc'


class DeviceIdMeta(object):
  """Class to provide platform-specific fields for DeviceInfo.

  Each platform is expected to subclass DeviceIdMeta and supply concrete
  implementations of all methods. We use a Python Abstract Base Class
  to protect against future versions. If we add fields to this class,
  any existing platform implementations will be prompted to add implementations
  (because they will fail to startup when their DeviceId fails to
  instantiate.
  """
  __metaclass__ = abc.ABCMeta

  @abc.abstractproperty
  def Manufacturer(self):
    return None

  @abc.abstractproperty
  def ManufacturerOUI(self):
    return None

  @abc.abstractproperty
  def ModelName(self):
    return None

  @abc.abstractproperty
  def Description(self):
    return None

  @abc.abstractproperty
  def SerialNumber(self):
    return None

  @abc.abstractproperty
  def HardwareVersion(self):
    return None

  @abc.abstractproperty
  def AdditionalHardwareVersion(self):
    return None

  @abc.abstractproperty
  def SoftwareVersion(self):
    return None

  @abc.abstractproperty
  def AdditionalSoftwareVersion(self):
    return None

  @abc.abstractproperty
  def ProductClass(self):
    return None

  @abc.abstractproperty
  def ModemFirmwareVersion(self):
    return None


def _GetUptime():
  """Return a string of the number of integer seconds since boot."""
  uptime = float(open(PROC_UPTIME).read().split()[0])
  return str(int(uptime))


#pylint: disable-msg=W0231
class DeviceInfo181Linux26(CATA181DEVICE.DeviceInfo):
  """Implements tr-181 DeviceInfo for Linux 2.6 and similar systems."""

  def __init__(self, device_id, ioloop=None):
    super(DeviceInfo181Linux26, self).__init__()
    assert isinstance(device_id, DeviceIdMeta)
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self._device_id = device_id
    self.MemoryStatus = MemoryStatusLinux26()
    self.ProcessStatus = ProcessStatusLinux26(ioloop=ioloop)
    self.Unexport('FirstUseDate')
    self.Unexport(lists='Location')
    self.Unexport(objects='NetworkProperties')
    self.Unexport('ProvisioningCode')
    self.Unexport(objects='ProxierInfo')
    self.TemperatureStatus = temperature.TemperatureStatus()
    self.VendorLogFileList = {}
    self.VendorConfigFileList = {}
    self.SupportedDataModelList = {}
    self.ProcessorList = {}
    self.X_CATAWAMPUS_ORG_LedStatusList = {}
    self._next_led_number = 1

  def __getattr__(self, name):
    """Allows passthrough of parameters to the platform-supplied device_id."""
    if hasattr(self._device_id, name):
      return getattr(self._device_id, name)
    else:
      raise AttributeError('No such attribute %s' % name)

  @property
  def UpTime(self):
    return _GetUptime()

  @property
  def VendorLogFileNumberOfEntries(self):
    return len(self.VendorLogFileList)

  @property
  def VendorConfigFileNumberOfEntries(self):
    return len(self.VendorConfigFileList)

  @property
  def LocationNumberOfEntries(self):
    return 0

  @property
  def ProcessorNumberOfEntries(self):
    return len(self.ProcessorList)

  @property
  def SupportedDataModelNumberOfEntries(self):
    return len(self.SupportedDataModelList)

  @property
  def X_CATAWAMPUS_ORG_LedStatusNumberOfEntries(self):
    return len(self.X_CATAWAMPUS_ORG_LedStatusList)

  def AddLedStatus(self, led):
    self.X_CATAWAMPUS_ORG_LedStatusList[self._next_led_number] = led
    self._next_led_number += 1


class MemoryStatusLinux26(BASE181DEVICE.DeviceInfo.MemoryStatus):
  """Abstraction to get memory information from the underlying platform.

  Reads /proc/meminfo to find TotalMem and FreeMem.
  """

  def __init__(self):
    super(MemoryStatusLinux26, self).__init__()
    (self._totalmem, self._freemem) = self._GetMemInfo()

  @property
  def Total(self):
    return self._totalmem

  @property
  def Free(self):
    return self._freemem

  def _GetMemInfo(self):
    """Fetch TotalMem and FreeMem from the underlying platform.

    Returns:
      a list of two integers, (totalmem, freemem)
    """
    totalmem = 0
    freemem = 0
    with open(PROC_MEMINFO) as pfile:
      for line in pfile:
        fields = line.split()
        name = fields[0]
        value = fields[1]
        if name == 'MemTotal:':
          totalmem = int(value)
        elif name == 'MemFree:':
          freemem = int(value)
    return (totalmem, freemem)


class ProcessStatusLinux26(BASE181DEVICE.DeviceInfo.ProcessStatus):
  """Get information about running processes on Linux 2.6.

  Reads /proc/<pid> to get information about processes.
  """
  # Field ordering in /proc/<pid>/stat
  _PID = 0
  _COMM = 1
  _STATE = 2
  _UTIME = 13
  _STIME = 14
  _PRIO = 17
  _RSS = 23

  def __init__(self, ioloop=None):
    super(ProcessStatusLinux26, self).__init__()
    tick = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
    self._msec_per_jiffy = 1000.0 / tick
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.scheduler = PERIODICCALL(self.CpuUsageTimer, 300 * 1000,
                                  io_loop=self.ioloop)
    self.scheduler.start()
    self.cpu_usage = 0.0
    self.cpu_used = 0
    self.cpu_total = 0
    self.ProcessList = tr.core.AutoDict('ProcessList',
                                        iteritems=self.IterProcesses,
                                        getitem=self.GetProcess)

  def _LinuxStateToTr181(self, linux_state):
    """Maps Linux process states to TR-181 process state names.

    Args:
      linux_state: One letter describing the state of the linux process,
        as described in proc(5). One of "RSDZTW"

    Returns:
      the tr-181 string describing the process state.
    """
    mapping = {
        'R': 'Running',
        'S': 'Sleeping',
        'D': 'Uninterruptible',
        'Z': 'Zombie',
        'T': 'Stopped',
        'W': 'Uninterruptible'}
    return mapping.get(linux_state, 'Sleeping')

  def _JiffiesToMsec(self, utime, stime):
    ticks = int(utime) + int(stime)
    msecs = ticks * self._msec_per_jiffy
    return int(msecs)

  def _RemoveParens(self, command):
    return command[1:-1]

  def _ProcFileName(self, pid):
    return '%s/%s/stat' % (SLASH_PROC, pid)

  def _ParseProcStat(self):
    """Compute CPU utilization using /proc/stat.

    Returns:
      (used, total)
      used: number of jiffies where CPU was active
      total: total number of jiffies including idle
    """
    with open(PROC_STAT) as f:
      for line in f:
        fields = line.split()
        if fields[0] == 'cpu':
          user = float(fields[1])
          nice = float(fields[2])
          syst = float(fields[3])
          idle = float(fields[4])
          iowt = float(fields[5])
          irq  = float(fields[6])
          sirq = float(fields[7])
          total = user + nice + syst + idle + iowt + irq + sirq
          used = total - idle
          return (used, total)
    return (0, 0)

  def CpuUsageTimer(self):
    """Called periodically to compute CPU utilization since last call."""
    (new_used, new_total) = self._ParseProcStat()
    total = new_total - self.cpu_total
    used = new_used - self.cpu_used
    if total == 0:
      self.cpu_usage = 0.0
    else:
      self.cpu_usage = (used / total) * 100.0
    self.cpu_total = new_total
    self.cpu_used = new_used

  @property
  def CPUUsage(self):
    return int(self.cpu_usage)

  @property
  def ProcessNumberOfEntries(self):
    return len(self.ProcessList)

  def GetProcess(self, pid):
    """Get a self.Process() object for the given pid."""
    try:
      with open(self._ProcFileName(pid)) as f:
        fields = f.read().split()
      p = self.Process(PID=int(fields[self._PID]),
                       Command=self._RemoveParens(fields[self._COMM]),
                       Size=int(fields[self._RSS]),
                       Priority=int(fields[self._PRIO]),
                       CPUTime=self._JiffiesToMsec(fields[self._UTIME],
                                                   fields[self._STIME]),
                       State=self._LinuxStateToTr181(fields[self._STATE]))
    except IOError:
      # This isn't an error. We have a list of files which existed the
      # moment the glob.glob was run. If a process exits before we get
      # around to reading it, its /proc files will go away.
      p = self.Process(PID=pid, Command='<exited>', Size=0, Priority=0,
                       CPUTime=0, State='X_CATAWAMPUS-ORG_Exited')
    return p

  def IterProcesses(self):
    """Walks through /proc/<pid>/stat to return a list of all processes."""
    for filename in glob.glob(self._ProcFileName('[0123456789]*')):
      pid = int(filename.split('/')[-2])
      proc = self.GetProcess(pid)
      yield pid, proc


class LedStatusReadFromFile(CATA181DEVICE.DeviceInfo.X_CATAWAMPUS_ORG_LedStatus):
  """X_CATAWAMPUS-ORG_LedStatus implementation which reads a line from a file."""

  def __init__(self, name, filename):
    super(LedStatusReadFromFile, self).__init__()
    self._name = name
    self._filename = filename

  @property
  def Name(self):
    return self._name

  @property
  def Status(self):
    return open(self._filename).readline().strip()


class DeviceInfo98Linux26(BASE98IGD.DeviceInfo):
  """Implementation of tr-98 DeviceInfo for Linux."""

  def __init__(self, device_id):
    super(DeviceInfo98Linux26, self).__init__()
    assert isinstance(device_id, DeviceIdMeta)
    self._device_id = device_id
    self.Unexport(params='DeviceLog')
    self.Unexport(params='EnabledOptions')
    self.Unexport(params='FirstUseDate')
    self.Unexport(params='ProvisioningCode')
    self.Unexport(lists='VendorConfigFile')
    self.VendorConfigFileNumberOfEntries = 0

  @property
  def SpecVersion(self):
    return '1.0'

  @property
  def UpTime(self):
    return _GetUptime()

  def __getattr__(self, name):
    if hasattr(self._device_id, name):
      return getattr(self._device_id, name)
    else:
      raise AttributeError('No such attribute %s' % name)


def main():
  dp = DeviceInfo181Linux26()
  #print tr.core.DumpSchema(dp)
  print tr.core.Dump(dp)

if __name__ == '__main__':
  main()
