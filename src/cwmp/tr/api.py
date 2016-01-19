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

"""External API for TR-069 support.

The classes here represent the ACS (Auto Configuration Server) and CPE
(Customer Premises Equipment) endpoints in the TR-069 standard API.  You can
hand them an hierarchy of tr.core.Exporter and use the
TR-069 access methods to manipulate it.

This file doesn't implement the XML (SOAP-like) wrapper around the TR-069
API calls; it's just a python version of the API.
"""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import download

from src.logger.HoneythingLogging import HTLogging


ht = HTLogging()

class SetParameterErrors(Exception):
  """A list of exceptions which occurred during a SetParameterValues transaction."""

  def __init__(self, error_list, msg):
    Exception.__init__(self, msg)
    self.error_list = error_list


class ParameterNameError(KeyError):
  """Raised for a SetParameterValue to a nonexistant parameter."""

  def __init__(self, parameter, msg):
    KeyError.__init__(self, msg)
    self.parameter = parameter


class ParameterTypeError(TypeError):
  """Raised when a SetParameterValue has the wrong type."""

  def __init__(self, parameter, msg):
    TypeError.__init__(self, msg)
    self.parameter = parameter


class ParameterValueError(ValueError):
  """Raised when a SetParameterValue has an invalid value."""

  def __init__(self, parameter, msg):
    ValueError.__init__(self, msg)
    self.parameter = parameter


class ParameterNotWritableError(AttributeError):
  """Raised when a SetParameterValue tries to set a read-only parameter."""

  def __init__(self, parameter, msg):
    AttributeError.__init__(self, msg)
    self.parameter = parameter


class TR069Service(object):
  """Represents a TR-069 SOAP RPC service."""

  def __init__(self):
    pass

  def GetRPCMethods(self):
    """Return a list of callable methods."""
    methods = []
    for i in sorted(dir(self)):
      if i[0].isupper():
        methods.append(i)
    return methods


class ACS(TR069Service):
  """Represents a TR-069 ACS (Auto Configuration Server)."""

  def __init__(self):
    TR069Service.__init__(self)
    self.cpe = None

  def Inform(self, cpe, root, events, max_envelopes,
             current_time, retry_count, parameter_list):
    """Called when the CPE first connects to the ACS."""
    #print 'ACS.Inform'
    ht.logger.info('ACS.Inform (CPE first connects to the ACS)')
    self.cpe = cpe

  def TransferComplete(self, command_key, fault_struct,
                       start_time, complete_time):
    """A file transfer requested by the ACS has been completed."""
    raise NotImplementedError()

  def AutonomousTransferComplete(self,
                                 announce_url, transfer_url,
                                 is_download, file_type,
                                 file_size, target_filename, fault_struct,
                                 start_time, complete_time):
    """A file transfer *not* requested by the ACS has been completed."""
    raise NotImplementedError()

  def Kicked(self, command, referer, arg, next_url):
    """Called whenever the CPE is kicked by the ACS."""
    raise NotImplementedError()

  def RequestDownload(self, file_type, file_type_args):
    """The CPE wants us to tell it to download something."""
    raise NotImplementedError()

  def DUStateChangeComplete(self, results, command_key):
    """A requested ChangeDUState has completed."""
    raise NotImplementedError()

  def AutonomousDUStateChangeComplete(self, results):
    """A DU state change that was not requested by the ACS has completed."""
    raise NotImplementedError()


class CPE(TR069Service):
  """Represents a TR-069 CPE (Customer Premises Equipment)."""

  def __init__(self, root):
    TR069Service.__init__(self)
    self._last_parameter_key = ''
    self.root = root
    self.download_manager = download.DownloadManager()
    self.transfer_complete_received_cb = None
    self.inform_response_received_cb = None

  def setCallbacks(self, send_transfer_complete,
                   transfer_complete_received,
                   inform_response_received):
    self.download_manager.send_transfer_complete = send_transfer_complete
    self.transfer_complete_received_cb = transfer_complete_received
    self.inform_response_received_cb = inform_response_received

  def startup(self):
    """Handle any initialization after reboot."""
    self.download_manager.RestoreDownloads()

  def _SetParameterKey(self, value):
    self._last_parameter_key = value

  def getParameterKey(self):
    return self._last_parameter_key

  def _SplitParameterName(self, name):
    """Split a name like Top.Object.1.Name into (Top.Object.1, Name)."""
    result = name.rsplit('.', 1)
    if len(result) == 2:
      return result[0], result[1]
    elif len(result) == 1:
      return None, result[0]
    elif not result:
      return None
    else:
      assert False

  def _SetParameterValue(self, name, value):
    """Given a parameter (which can include an object), set its value."""
    if name == 'ParameterKey':
      self._SetParameterKey(value)
      return None
    else:
      return self.root.SetExportParam(name, value)

  def _ConcludeTransaction(self, objects, do_commit):
    """Commit or abandon  all pending writes.

    Args:
      objects: list of dirty objects to commit
      do_commit: call CommitTransaction if True, else AbandonTransaction

    Returns: the response code to return

    SetParameterValues is an atomic transaction, all parameters are set or
    none of them are. We set obj.dirty and call obj.StartTransaction on
    every object written to. Now we walk back through the dirtied objects
    to finish the transaction.
    """
    # TODO(dgentry) At some point there will be interdependencies between
    #   objects. We'll need to develop a means to express those dependencies
    #   and walk the dirty objects in a specific order.
    for obj in objects:
      assert obj.dirty
      obj.dirty = False
      if do_commit:
        obj.CommitTransaction()
      else:
        obj.AbandonTransaction()
    return 0  # all values changed successfully

  def SetParameterValues(self, parameter_list, parameter_key):
    """Sets parameters on some objects."""
    dirty = set()
    error_list = []
    for name, value in parameter_list:
      obj = None
      try:
        obj = self._SetParameterValue(name, value)
      except TypeError as e:
        error_list.append(ParameterTypeError(parameter=name, msg=str(e)))
      except ValueError as e:
        error_list.append(ParameterValueError(parameter=name, msg=str(e)))
      except KeyError as e:
        error_list.append(ParameterNameError(parameter=name, msg=str(e)))
      except AttributeError as e:
        error_list.append(ParameterNotWritableError(parameter=name, msg=str(e)))

      if obj:
        dirty.add(obj)
    if error_list:
      self._ConcludeTransaction(objects=dirty, do_commit=False)
      raise SetParameterErrors(error_list=error_list,
                               msg='Transaction Errors: %d' % len(error_list))
    else:
      self._SetParameterKey(parameter_key)
      return self._ConcludeTransaction(dirty, True)

  def _GetParameterValue(self, name):
    """Given a parameter (which can include an object), return its value."""
    if name == 'ParameterKey':
      return self._last_parameter_key
    else:
      return self.root.GetExport(name)

  def GetParameterValues(self, parameter_names):
    """Gets parameters from some objects.

    Args:
      parameter_names: a list of parameter name strings.
    Returns:
      A list of (name, value) tuples.
    """
    result = []
    for param in parameter_names:
      if not param:
        # tr69 A.3.2.2: empty string indicates top of the name hierarchy.
        paramlist = self.root.ListExports(None, False)
        parameter_names.extend(paramlist)
      elif param.endswith('.'):
        paramlist = self.root.ListExports(param[:-1], False)
        for p in paramlist:
          parameter_names.append(param + p)
      else:
        result.append((param, self._GetParameterValue(param)))
    return result

  def GetParameterNames(self, parameter_path, next_level_only):
    """Get the names of parameters or objects (possibly recursively)."""
    return self.root.ListExports(parameter_path, not next_level_only)

  def _SetParameterAttribute(self, param, attr, attr_value):
    """Set an attribute of a parameter."""
    (param, unused_param_name) = self._SplitParameterName(param)
    self.root.SetExportAttr(param, attr, attr_value)

  def SetParameterAttributes(self, parameter_list):
    """Set attributes (access control, notifications) on some parameters."""
    param_name = parameter_list['Name']
    for attr, attr_value in parameter_list.iteritems():
      if attr != 'Name':
        self._SetParameterAttribute(param_name, attr, attr_value)

  def GetParameterAttributes(self, parameter_names):
    """Get attributes (access control, notifications) on some parameters."""
    raise NotImplementedError()

  def AddObject(self, object_name, parameter_key):
    """Create a new object with default parameters."""
    assert object_name.endswith('.')
    #pylint: disable-msg=W0612
    (idx, obj) = self.root.AddExportObject(object_name[:-1])
    self._SetParameterKey(parameter_key)
    return (idx, 0)  # successfully created

  def DeleteObject(self, object_name, parameter_key):
    """Delete an object and its sub-objects/parameters."""
    assert object_name.endswith('.')
    path = object_name.split('.')
    self.root.DeleteExportObject('.'.join(path[:-2]), path[-2])
    self._SetParameterKey(parameter_key)
    return 0  # successfully deleted

  def Download(self, command_key, file_type, url, username, password,
               file_size, target_filename, delay_seconds,
               success_url, failure_url):  #pylint: disable-msg=W0613
    """Initiate a download immediately or after a delay."""
    return self.download_manager.NewDownload(
        command_key=command_key,
        file_type=file_type,
        url=url,
        username=username,
        password=password,
        file_size=file_size,
        target_filename=target_filename,
        delay_seconds=delay_seconds)

  def Reboot(self, command_key):
    """Reboot the CPE."""
    self.download_manager.Reboot(command_key)

  def GetQueuedTransfers(self):
    """Retrieve a list of queued file transfers (downloads and uploads)."""
    return self.download_manager.GetAllQueuedTransfers()

  def ScheduleInform(self, delay_seconds, command_key):
    """Request that this CPE call Inform() at some point in the future."""
    raise NotImplementedError()

  def SetVouchers(self, voucher_list):
    """Set option vouchers (deprecated)."""
    raise NotImplementedError()

  def GetOptions(self, option_name):
    """Get option vouchers (deprecated)."""
    raise NotImplementedError()

  def Upload(self, command_key, file_type, url,
             username, password, delay_seconds):
    """Initiate a file upload immediately or after a delay."""
    raise NotImplementedError()

  def FactoryReset(self):
    """Factory reset the CPE."""
    raise NotImplementedError()

  def GetAllQueuedTransfers(self):
    """Get a list of all uploads/downloads that are still in the queue."""
    return self.download_manager.GetAllQueuedTransfers()

  def ScheduleDownload(self, command_key, file_type, url,
                       username, password, file_size, target_filename,
                       time_window_list):
    """Schedule a download for some time in the future."""
    raise NotImplementedError()

  def CancelTransfer(self, command_key):
    """Cancel a scheduled file transfer."""
    return self.download_manager.CancelTransfer(command_key)

  def ChangeDUState(self, operations, command_key):
    """Trigger an install, update, or uninstall operation."""
    raise NotImplementedError()

  def transferCompleteResponseReceived(self):
    if self.transfer_complete_received_cb:
      self.transfer_complete_received_cb()
    return self.download_manager.TransferCompleteResponseReceived()

  def informResponseReceived(self):
    if self.inform_response_received_cb:
      self.inform_response_received_cb()
