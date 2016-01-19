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

"""Implementation of tr-140 Storage Services objects."""

__author__ = 'dgentry@google.com (Denton Gentry)'


import ctypes
import fcntl
import os
import os.path
import re
import subprocess
import tr.core
import tr.tr140_v1_1
import tr.x_catawampus_storage_1_0


BASESTORAGE = tr.x_catawampus_storage_1_0.X_CATAWAMPUS_ORG_Storage_v1_0.StorageService


class MtdEccStats(ctypes.Structure):
  """<mtd/mtd-abi.h> struct mtd_ecc_stats."""

  _fields_ = [('corrected', ctypes.c_uint32),
              ('failed', ctypes.c_uint32),
              ('badblocks', ctypes.c_uint32),
              ('bbtblocks', ctypes.c_uint32)]


def _GetMtdStats(mtddev):
  """Return the MtdEccStats for the given mtd device.

  Arguments:
    mtddev: the string path to the device, ex: '/dev/mtd14'
  Raises:
    IOError: if the ioctl fails.
  Returns:
    an MtdEccStats.
  """

  ECCGETSTATS = 0x40104d12  # ECCGETSTATS _IOR('M', 18, struct mtd_ecc_stats)
  with open(mtddev, 'r') as f:
    ecc = MtdEccStats()
    if fcntl.ioctl(f, ECCGETSTATS, ctypes.addressof(ecc)) != 0:
      raise IOError('ECCGETSTATS failed')
    return ecc


# Unit tests can override these
GETMTDSTATS = _GetMtdStats
PROC_FILESYSTEMS = '/proc/filesystems'
PROC_MOUNTS = '/proc/mounts'
SLASHDEV = '/dev/'
SMARTCTL = '/usr/sbin/smartctl'
STATVFS = os.statvfs
SYS_BLOCK = '/sys/block/'
SYS_UBI = '/sys/class/ubi/'


def _FsType(fstype):
  supported = {'vfat': 'FAT32', 'ext2': 'ext2', 'ext3': 'ext3',
               'ext4': 'ext4', 'msdos': 'FAT32', 'xfs': 'xfs',
               'reiserfs': 'REISER'}
  if fstype in supported:
    return supported[fstype]
  else:
    return 'X_CATAWAMPUS-ORG_' + fstype


def _IsSillyFilesystem(fstype):
  """Filesystems which are not interesting to export to the ACS."""
  SILLY = frozenset(['devtmpfs', 'proc', 'sysfs', 'usbfs', 'devpts',
                     'rpc_pipefs', 'autofs', 'nfsd', 'binfmt_misc', 'fuseblk'])
  return fstype in SILLY


def _GetFieldFromOutput(prefix, output, default=''):
  """Search output for line of the form 'Foo: Bar', return 'Bar'."""
  field_re = re.compile(prefix + '\s*(\S+)')
  for line in output.splitlines():
    result = field_re.search(line)
    if result is not None:
      return result.group(1).strip()
  return default


def _ReadOneLine(filename, default):
  """Read one line from a file. Return default if anything fails."""
  try:
    f = open(filename, 'r')
    return f.readline().strip()
  except IOError:
    return default


def IntFromFile(filename):
  """Read one line from a file and return an int, or zero if an error occurs."""
  try:
    buf = _ReadOneLine(filename, '0')
    return int(buf)
  except ValueError:
    return 0


class LogicalVolumeLinux26(BASESTORAGE.LogicalVolume):
  """Implementation of tr-140 StorageService.LogicalVolume for Linux FS."""

  def __init__(self, rootpath, fstype):
    BASESTORAGE.LogicalVolume.__init__(self)
    self.rootpath = rootpath
    self.fstype = fstype
    self.Unexport('Alias')
    self.Unexport('Encrypted')
    self.Unexport('ThresholdReached')
    self.Unexport('PhysicalReference')
    self.FolderList = {}
    self.ThresholdLimit = 0

  @property
  def Name(self):
    return self.rootpath

  @property
  def Status(self):
    return 'Online'

  @property
  def Enable(self):
    return True

  @property
  def FileSystem(self):
    return self.fstype

  # TODO(dgentry) need @sessioncache decorator
  def _GetStatVfs(self):
    return STATVFS(self.rootpath)

  @property
  def Capacity(self):
    vfs = self._GetStatVfs()
    return int(vfs.f_blocks * vfs.f_bsize / 1024 / 1024)

  @property
  def ThresholdReached(self):
    vfs = self._GetStatVfs()
    require = self.ThresholdLimit * 1024 * 1024
    avail = vfs.f_bavail * vfs.f_bsize
    return True if avail < require else False

  @property
  def UsedSpace(self):
    vfs = self._GetStatVfs()
    b_used = vfs.f_blocks - vfs.f_bavail
    return int(b_used * vfs.f_bsize / 1024 / 1024)

  @property
  def X_CATAWAMPUS_ORG_ReadOnly(self):
    ST_RDONLY = 0x0001
    vfs = self._GetStatVfs()
    return True if vfs.f_flag & ST_RDONLY else False

  @property
  def FolderNumberOfEntries(self):
    return len(self.FolderList)


class PhysicalMediumDiskLinux26(BASESTORAGE.PhysicalMedium):
  """tr-140 PhysicalMedium implementation for non-removable disks."""

  CONNECTION_TYPES = frozenset(
      ['USB 1.1', 'USB 2.0', 'IEEE1394', 'IEEE1394b', 'IDE', 'EIDE',
       'ATA/33', 'ATA/66', 'ATA/100', 'ATA/133', 'SATA/150', 'SATA/300',
       'SCSI-1', 'Fast SCSI', 'Fast-Wide SCSI', 'Ultra SCSI', 'Ultra Wide SCSI',
       'Ultra2 SCSI', 'Ultra2 Wide SCSI', 'Ultra3 SCSI', 'Ultra-320 SCSI',
       'Ultra-640 SCSI', 'SSA', 'SSA-40', 'Fibre Channel'])

  def __init__(self, dev, conn_type=None):
    BASESTORAGE.PhysicalMedium.__init__(self)
    self.dev = dev
    self.name = dev
    self.Unexport('Alias')
    # TODO(dgentry) read SMART attribute for PowerOnHours
    self.Unexport('Uptime')
    # TODO(dgentry) What does 'Standby' or 'Offline' mean?
    self.Unexport('Status')
    if conn_type is None:
      # transport is really, really hard to infer programatically.
      # If platform code doesn't provide it, don't try to guess.
      self.Unexport('ConnectionType')
    else:
      # Provide a hint to the platform code: use a valid enumerated string,
      # or define a vendor extension. Don't just make something up.
      assert conn_type[0:1] == 'X_' or conn_type in self.CONNECTION_TYPES
    self.conn_type = conn_type

  # TODO(dgentry) need @sessioncache decorator
  def _GetSmartctlOutput(self):
    """Return smartctl info and health output."""
    dev = SLASHDEV + self.dev
    smart = subprocess.Popen([SMARTCTL, '--info', '--health', dev],
                             stdout=subprocess.PIPE)
    out, _ = smart.communicate(None)
    return out

  def GetName(self):
    return self.name

  def SetName(self, value):
    self.name = value

  Name = property(GetName, SetName, None, 'PhysicalMedium.Name')

  @property
  def Vendor(self):
    filename = SYS_BLOCK + '/' + self.dev + '/device/vendor'
    vendor = _ReadOneLine(filename=filename, default='')
    # /sys/block/?da/device/vendor is often 'ATA'. Not useful.
    return '' if vendor == 'ATA' else vendor

  @property
  def Model(self):
    filename = SYS_BLOCK + '/' + self.dev + '/device/model'
    return _ReadOneLine(filename=filename, default='')

  @property
  def SerialNumber(self):
    return _GetFieldFromOutput(prefix='Serial Number:',
                               output=self._GetSmartctlOutput(),
                               default='')

  @property
  def FirmwareVersion(self):
    return _GetFieldFromOutput(prefix='Firmware Version:',
                               output=self._GetSmartctlOutput(),
                               default='')

  @property
  def ConnectionType(self):
    return self.conn_type

  @property
  def Removable(self):
    return False

  @property
  def Capacity(self):
    """Return capacity in Megabytes."""
    filename = SYS_BLOCK + '/' + self.dev + '/size'
    size = _ReadOneLine(filename=filename, default='0')
    try:
      # TODO(dgentry) Do 4k sector drives populate size in 512 byte blocks?
      return int(size) * 512 / 1048576
    except ValueError:
      return 0

  @property
  def SMARTCapable(self):
    capable = _GetFieldFromOutput(prefix='SMART support is: Enab',
                                  output=self._GetSmartctlOutput(),
                                  default=None)
    return True if capable else False

  @property
  def Health(self):
    health = _GetFieldFromOutput(
        prefix='SMART overall-health self-assessment test result:',
        output=self._GetSmartctlOutput(),
        default='')
    if health == 'PASSED':
      return 'OK'
    elif health.find('FAIL') >= 0:
      return 'Failing'
    else:
      return 'Error'

  @property
  def HotSwappable(self):
    filename = SYS_BLOCK + '/' + self.dev + '/removable'
    removable = _ReadOneLine(filename=filename, default='0').strip()
    return False if removable == '0' else True


class FlashSubVolUbiLinux26(BASESTORAGE.X_CATAWAMPUS_ORG_FlashMedia.SubVolume):
  """Catawampus Storage Flash SubVolume implementation for UBI volumes."""

  def __init__(self, ubivol):
    BASESTORAGE.X_CATAWAMPUS_ORG_FlashMedia.SubVolume.__init__(self)
    self.ubivol = ubivol

  @property
  def DataMBytes(self):
    bytesiz = IntFromFile(os.path.join(SYS_UBI, self.ubivol, 'data_bytes'))
    return int(bytesiz / 1024 / 1024)

  @property
  def Name(self):
    return _ReadOneLine(os.path.join(SYS_UBI, self.ubivol, 'name'), self.ubivol)

  @property
  def Status(self):
    corr = IntFromFile(os.path.join(SYS_UBI, self.ubivol, 'corrupted'))
    return 'OK' if corr == 0 else 'Corrupted'


class FlashMediumUbiLinux26(BASESTORAGE.X_CATAWAMPUS_ORG_FlashMedia):
  """Catawampus Storage FlashMedium implementation for UBI volumes."""

  def __init__(self, ubiname):
    BASESTORAGE.X_CATAWAMPUS_ORG_FlashMedia.__init__(self)
    self.ubiname = ubiname
    self.SubVolumeList = {}
    num = 0
    for i in range(128):
      subvolname = ubiname + '_' + str(i)
      try:
        if os.stat(os.path.join(SYS_UBI, self.ubiname, subvolname)):
          self.SubVolumeList[str(num)] = FlashSubVolUbiLinux26(subvolname)
          num += 1
      except OSError:
        pass

  @property
  def BadEraseBlocks(self):
    return IntFromFile(os.path.join(SYS_UBI, self.ubiname, 'bad_peb_count'))

  @property
  def CorrectedErrors(self):
    mtdnum = IntFromFile(os.path.join(SYS_UBI, self.ubiname, 'mtd_num'))
    ecc = GETMTDSTATS(os.path.join(SLASHDEV, 'mtd' + str(mtdnum)))
    return ecc.corrected

  @property
  def EraseBlockSize(self):
    return IntFromFile(os.path.join(SYS_UBI, self.ubiname, 'eraseblock_size'))

  @property
  def IOSize(self):
    return IntFromFile(os.path.join(SYS_UBI, self.ubiname, 'min_io_size'))

  @property
  def MaxEraseCount(self):
    return IntFromFile(os.path.join(SYS_UBI, self.ubiname, 'max_ec'))

  @property
  def SubVolumeNumberOfEntries(self):
    return len(self.SubVolumeList)

  @property
  def Name(self):
    return self.ubiname

  @property
  def ReservedEraseBlocks(self):
    return IntFromFile(os.path.join(SYS_UBI, self.ubiname, 'reserved_for_bad'))

  @property
  def TotalEraseBlocks(self):
    return IntFromFile(os.path.join(SYS_UBI, self.ubiname, 'total_eraseblocks'))

  @property
  def UncorrectedErrors(self):
    mtdnum = IntFromFile(os.path.join(SYS_UBI, self.ubiname, 'mtd_num'))
    ecc = GETMTDSTATS(os.path.join(SLASHDEV, 'mtd' + str(mtdnum)))
    return ecc.failed


class CapabilitiesNoneLinux26(BASESTORAGE.Capabilities):
  """Trivial tr-140 StorageService.Capabilities, all False."""

  def __init__(self):
    BASESTORAGE.Capabilities.__init__(self)

  @property
  def FTPCapable(self):
    return False

  @property
  def HTTPCapable(self):
    return False

  @property
  def HTTPSCapable(self):
    return False

  @property
  def HTTPWritable(self):
    return False

  @property
  def SFTPCapable(self):
    return False

  @property
  def SupportedFileSystemTypes(self):
    """Returns possible filesystems.

    Parses /proc/filesystems, omit any defined as uninteresting in
    _IsSillyFileSystem(), and return the rest.

    Returns:
      a string of comma-separated filesystem types.
    """
    fslist = set()
    f = open(PROC_FILESYSTEMS)
    for line in f:
      if line.find('nodev') >= 0:
        # rule of thumb to skip internal, non-interesting filesystems
        continue
      fstype = line.strip()
      if _IsSillyFilesystem(fstype):
        continue
      fslist.add(_FsType(fstype))
    return ','.join(sorted(fslist, key=str.lower))

  @property
  def SupportedNetworkProtocols(self):
    return ''

  @property
  def SupportedRaidTypes(self):
    return ''

  @property
  def VolumeEncryptionCapable(self):
    return False


class StorageServiceLinux26(BASESTORAGE):
  """Implements a basic tr-140 for Linux 2.6-ish systems.

  This class implements no network file services, it only exports
  the LogicalVolume information.
  """

  def __init__(self):
    BASESTORAGE.__init__(self)
    self.Capabilities = CapabilitiesNoneLinux26()
    self.Unexport('Alias')
    self.Unexport(objects='NetInfo')
    self.Unexport(objects='NetworkServer')
    self.Unexport(objects='FTPServer')
    self.Unexport(objects='SFTPServer')
    self.Unexport(objects='HTTPServer')
    self.Unexport(objects='HTTPSServer')
    self.PhysicalMediumList = {}
    self.StorageArrayList = {}
    self.LogicalVolumeList = tr.core.AutoDict(
        'LogicalVolumeList', iteritems=self.IterLogicalVolumes,
        getitem=self.GetLogicalVolumeByIndex)
    self.UserAccountList = {}
    self.UserGroupList = {}
    self.X_CATAWAMPUS_ORG_FlashMediaList = {}

  @property
  def Enable(self):
    # TODO(dgentry): tr-140 says this is supposed to be writable
    return True

  @property
  def PhysicalMediumNumberOfEntries(self):
    return len(self.PhysicalMediumList)

  @property
  def StorageArrayNumberOfEntries(self):
    return len(self.StorageArrayList)

  @property
  def LogicalVolumeNumberOfEntries(self):
    return len(self.LogicalVolumeList)

  @property
  def UserAccountNumberOfEntries(self):
    return len(self.UserAccountList)

  @property
  def UserGroupNumberOfEntries(self):
    return len(self.UserGroupList)

  @property
  def X_CATAWAMPUS_ORG_FlashMediaNumberOfEntries(self):
    return len(self.X_CATAWAMPUS_ORG_FlashMediaList)

  def _ParseProcMounts(self):
    """Return list of (mount point, filesystem type) tuples."""
    mounts = dict()
    try:
      f = open(PROC_MOUNTS)
    except IOError:
      return []
    for line in f:
      fields = line.split()
      # ex: /dev/mtdblock9 / squashfs ro,relatime 0 0
      if len(fields) < 6:
        continue
      fsname = fields[0]
      mountpoint = fields[1]
      fstype = fields[2]
      if fsname == 'none' or _IsSillyFilesystem(fstype):
        continue
      mounts[mountpoint] = _FsType(fstype)
    return sorted(mounts.items())

  def GetLogicalVolume(self, fstuple):
    """Get an LogicalVolume object for a mounted filesystem."""
    (mountpoint, fstype) = fstuple
    return LogicalVolumeLinux26(mountpoint, fstype)

  def IterLogicalVolumes(self):
    """Retrieves a list of all mounted filesystems."""
    fstuples = self._ParseProcMounts()
    for idx, fstuple in enumerate(fstuples):
      yield idx, self.GetLogicalVolume(fstuple)

  def GetLogicalVolumeByIndex(self, index):
    fstuples = self._ParseProcMounts()
    if index >= len(fstuples):
      raise IndexError('No such object LogicalVolume.{0}'.format(index))
    return self.GetLogicalVolume(fstuples[index])


def main():
  pass

if __name__ == '__main__':
  main()
