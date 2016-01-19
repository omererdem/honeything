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
#pylint: disable-msg=W0404
#
"""Implement handling for the X_GOOGLE-COM_GFIBERTV vendor data model."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import copy
import errno
import os
import xmlrpclib
import google3
import tr.core
import tr.cwmpbool
import tr.helpers
import tr.x_gfibertv_1_0
BASETV = tr.x_gfibertv_1_0.X_GOOGLE_COM_GFIBERTV_v1_0.X_GOOGLE_COM_GFIBERTV

NICKFILE = '/tmp/nicknames'
NICKFILE_TMP = '/tmp/nicknames.tmp'
BTDEVICES = '/user/bsa/bt_devices.xml'
BTDEVICES_TMP = '/user/bsa/bt_devices.xml.tmp'
BTHHDEVICES = '/user/bsa/bt_hh_devices.xml'
BTHHDEVICES_TMP = '/user/bsa/bt_hh_devices.xml.tmp'
BTCONFIG = '/user/bsa/bt_config.xml'
BTCONFIG_TMP = '/user/bsa/bt_config.xml.tmp'
BTNOPAIRING = '/usr/bsa/nopairing'


class GFiberTvConfig(object):
  """Class to store configuration settings for GFiberTV."""
  pass


class PropertiesConfig(object):
  """Class to store configuration settings for DeviceProperties."""
  pass


class GFiberTv(BASETV):
  """Implementation of x-gfibertv.xml."""

  def __init__(self, mailbox_url):
    super(GFiberTv, self).__init__()
    self.Mailbox = GFiberTvMailbox(mailbox_url)
    self.config = GFiberTvConfig()
    self.config.nicknames = dict()
    self.config_old = None
    self.config.bt_devices = None
    self.config.bt_hh_devices = None
    self.config.bt_config = None
    self.DevicePropertiesList = tr.core.AutoDict(
        'X_GOOGLE_COM_GFIBERTV.DevicePropertiesList',
        iteritems=self.IterProperties, getitem=self.GetProperties,
        setitem=self.SetProperties, delitem=self.DelProperties)


  class DeviceProperties(BASETV.DeviceProperties):
    """Implementation of gfibertv.DeviceProperties."""

    def __init__(self):
      super(GFiberTv.DeviceProperties, self).__init__()
      self.config = PropertiesConfig()
      # nick_name is a unicode string.
      self.config.nick_name = ''
      self.config.serial_number = ''

    def StartTransaction(self):
      # NOTE(jnewlin): If an inner object is added, we need to do deepcopy.
      self.config_old = copy.copy(self.config)

    def AbandonTransaction(self):
      self.config = self.config_old
      self.config_old = None

    def CommitTransaction(self):
      self.config_old = None

    @property
    def NickName(self):
      return self.config.nick_name.decode('utf-8')

    @NickName.setter
    def NickName(self, value):
      # TODO(jnewlin): Need some sanity here so the user can't enter
      # a value that hoses the file, like a carriage return or newline.
      tmp_uni = unicode(value, 'utf-8')
      tmp_uni = tmp_uni.replace(u'\n', u'')
      tmp_uni = tmp_uni.replace(u'\r', u'')
      self.config.nick_name = tmp_uni

    @property
    def SerialNumber(self):
      return self.config.serial_number

    @SerialNumber.setter
    def SerialNumber(self, value):
      self.config.serial_number = value

  def StartTransaction(self):
    assert self.config_old is None
    self.config_old = copy.copy(self.config)

  def AbandonTransaction(self):
    self.config = self.config_old
    self.config_old = None

  def CommitTransaction(self):
    """Write out the config file for Sage."""
    if self.config.nicknames:
      with file(NICKFILE_TMP, 'w') as f:
        serials = []
        for nn in self.config.nicknames.itervalues():
          f.write('%s/nickname=%s\n' % (
              nn.SerialNumber, nn.config.nick_name.encode('unicode-escape')))
          serials.append(nn.SerialNumber)
        f.write('SERIALS=%s\n' % ','.join(serials))
      os.rename(NICKFILE_TMP, NICKFILE)

    if self.config.bt_devices != None:
      tr.helpers.WriteFileAtomic(BTDEVICES_TMP, BTDEVICES,
                                 self.config.bt_devices)
      self.config.bt_devices = None

    if self.config.bt_hh_devices != None:
      tr.helpers.WriteFileAtomic(BTHHDEVICES_TMP, BTHHDEVICES,
                         self.config.bt_hh_devices)
      self.config.bt_hh_devices = None

    if self.config.bt_config != None:
      tr.helpers.WriteFileAtomic(BTCONFIG_TMP, BTCONFIG, self.config.bt_config)
      self.config.bt_config = None
    self.config_old = None

  @property
  def DevicePropertiesNumberOfEntries(self):
    return len(self.config.nicknames)

  def IterProperties(self):
    return self.config.nicknames.iteritems()

  def GetProperties(self, key):
    return self.config.nicknames[key]

  def SetProperties(self, key, value):
    self.config.nicknames[key] = value

  def DelProperties(self, key):
    del self.config.nicknames[key]

  @property
  def BtDevices(self):
    try:
      with file(BTDEVICES, 'r') as f:
        return f.read()
    except IOError as e:
      # If the file doesn't exist for some reason, just return an empty
      # string, otherwise throw the exception, which should get propagated
      # back to the ACS.
      if e.errno == errno.ENOENT:
        return ''
      raise

  @property
  def XX(self):
    return True

  @property
  def BtNoPairing(self):
    return os.access(BTNOPAIRING, os.R_OK)

  @BtNoPairing.setter
  def BtNoPairing(self, value):
    no_pairing = tr.cwmpbool.parse(value)
    if no_pairing:
      with open(BTNOPAIRING, 'w') as f:
        pass
    else:
      try:
        os.unlink(BTNOPAIRING)
      except OSError as e:
        if e.errno != errno.ENOENT:
          raise

  @BtDevices.setter
  def BtDevices(self, value):
    self.config.bt_devices = value

  @property
  def BtHHDevices(self):
    try:
      with file(BTHHDEVICES, 'r') as f:
        return f.read()
    # IOError is thrown if the file doesn't exist.
    except IOError:
      return ''

  @BtHHDevices.setter
  def BtHHDevices(self, value):
    self.config.bt_hh_devices = value

  @property
  def BtConfig(self):
    try:
      with file(BTCONFIG, 'r') as f:
        return f.read()
    # IOError is thrown if the file doesn't exist.
    except IOError:
      return ''

  @BtConfig.setter
  def BtConfig(self, value):
    self.config.bt_config = value

class GFiberTvMailbox(BASETV.Mailbox):
  """Implementation of x-gfibertv.xml."""

  def __init__(self, url):
    super(GFiberTvMailbox, self).__init__()
    self.rpcclient = xmlrpclib.ServerProxy(url)
    self.Name = ''
    self.Node = ''

  def GetValue(self):
    if not self.Name:
      return None
    try:
      return str(self.rpcclient.GetProperty(self.Name, self.Node))
    except xmlrpclib.Fault:
      raise IndexError('No such Property %s:%s' % (self.Node, self.Name))
    except (xmlrpclib.ProtocolError, IOError):
      raise IndexError(
          'Unable to access Property %s:%s' % (self.Node, self.Name))

  def SetValue(self, value):
    try:
      return str(self.rpcclient.SetProperty(self.Name, value, self.Node))
    except xmlrpclib.Fault:
      raise IndexError('No such Property %s:%s' % (self.Node, self.Name))
    except (xmlrpclib.ProtocolError, IOError):
      raise IndexError(
          'Unable to access Property %s:%s' % (self.Node, self.Name))

  Value = property(GetValue, SetValue, None,
                   'X_GOOGLE_COM_GFIBERTV_v1_0.Mailbox.Value')

  @property
  def NodeList(self):
    try:
      return str(', '.join(self.rpcclient.ListNodes()))
    except (xmlrpclib.Fault, xmlrpclib.ProtocolError, IOError), e:
      print 'gfibertv.NodeList: %s' % e
      return {}
