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

"""Encodings for the SOAP-based protocol used by TR-069."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import re
import xml.etree.ElementTree
import google3
import xmlwitch

from src.logger.HoneythingLogging import HTLogging

ht = HTLogging()

class FaultType(object):
  SERVER = 'Server'
  CLIENT = 'Client'


class CpeFault(object):
  """CPE Fault codes for SOAP:Fault messages."""

  METHOD_NOT_SUPPORTED = 9000, FaultType.SERVER
  REQUEST_DENIED = 9001, FaultType.SERVER
  INTERNAL_ERROR = 9002, FaultType.SERVER
  INVALID_ARGUMENTS = 9003, FaultType.CLIENT
  RESOURCES_EXCEEDED = 9004, FaultType.SERVER
  INVALID_PARAM_NAME = 9005, FaultType.CLIENT
  INVALID_PARAM_TYPE = 9006, FaultType.CLIENT
  INVALID_PARAM_VALUE = 9007, FaultType.CLIENT
  NON_WRITABLE_PARAM = 9008, FaultType.CLIENT
  NOTIFICATION_REQUEST_REJECTED = 9009, FaultType.SERVER
  DOWNLOAD_FAILURE = 9010, FaultType.SERVER
  UPLOAD_FAILURE = 9011, FaultType.SERVER
  FILE_TRANSFER_AUTH = 9012, FaultType.SERVER
  FILE_TRANSFER_PROTOCOL = 9013, FaultType.SERVER
  DOWNLOAD_MULTICAST = 9014, FaultType.SERVER
  DOWNLOAD_CONNECT = 9015, FaultType.SERVER
  DOWNLOAD_ACCESS = 9016, FaultType.SERVER
  DOWNLOAD_INCOMPLETE = 9017, FaultType.SERVER
  DOWNLOAD_CORRUPTED = 9018, FaultType.SERVER
  DOWNLOAD_AUTH = 9019, FaultType.SERVER
  DOWNLOAD_TIMEOUT = 9020, FaultType.CLIENT
  DOWNLOAD_CANCEL_NOTPERMITTED = 9021, FaultType.CLIENT
  # codes 9800-9899: vendor-defined faults


class AcsFault(object):
  """ACS Fault codes for SOAP:Fault messages."""

  METHOD_NOT_SUPPORTED = 8000, FaultType.SERVER
  REQUEST_DENIED = 8001, FaultType.SERVER
  INTERNAL_ERROR = 8002, FaultType.SERVER
  INVALID_ARGUMENTS = 8003, FaultType.CLIENT
  RESOURCES_EXCEEDED = 8004, FaultType.SERVER
  RETRY_REQUEST = 8005, FaultType.SERVER
  # codes 8800-8899: vendor-defined faults


class _Enterable(object):
  def __init__(self, iterable):
    self.iter = iterable

  def __iter__(self):
    return self.iter

  def __enter__(self):
    return self.iter.next()

  def __exit__(self, type, value, tb):
    try:
      self.iter.next()
    except StopIteration:
      pass


def Enterable(func):
  def Wrap(*args, **kwargs):
    return _Enterable(func(*args, **kwargs))
  return Wrap


@Enterable
def Envelope(request_id, hold_requests):
  xml = xmlwitch.Builder(version='1.0', encoding='utf-8')
  attrs = {'xmlns:soap': 'http://schemas.xmlsoap.org/soap/envelope/',
           'xmlns:soap-enc': 'http://schemas.xmlsoap.org/soap/encoding/',
           'xmlns:xsd': 'http://www.w3.org/2001/XMLSchema',
           'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
           'xmlns:cwmp': 'urn:dslforum-org:cwmp-1-2'}
  with xml['soap:Envelope'](**attrs):
    with xml['soap:Header']:
      must_understand_attrs = {'soap:mustUnderstand': '1'}
      if request_id is not None:
        xml['cwmp:ID'](str(request_id), **must_understand_attrs)
      if hold_requests is not None:
        xml['cwmp:HoldRequests'](hold_requests and '1' or '0',
                                 **must_understand_attrs)
    with xml['soap:Body']:
      yield xml


@Enterable
def Fault(xml, fault, faultstring):
  fault_code, fault_type = fault
  with xml['soap:Fault']:
    xml.faultcode(fault_type)
    xml.faultstring('CWMP fault')
    with xml.detail:
      with xml['cwmp:Fault']:
        xml.FaultCode(str(fault_code))
        xml.FaultString(faultstring)
        yield xml


def GetParameterNames(xml, path, nextlevel):
  with xml['cwmp:GetParameterNames']:
    xml.ParameterPath(path)
    xml.NextLevel(nextlevel and '1' or '0')
  return xml


def SetParameterValuesFault(xml, faults):
  with Fault(xml, CpeFault.INVALID_ARGUMENTS, 'Invalid arguments') as xml:
    for parameter, code, string in faults:
      with xml.SetParameterValuesFault:
        xml.ParameterName(parameter)
        xml.FaultCode(str(int(code[0])))
        xml.FaultString(string)
  return xml


def SimpleFault(xml, cpefault, faultstring):
  with Fault(xml, cpefault, faultstring) as xml:
    return xml


def _StripNamespace(tagname):
  return re.sub(r'^\{.*\}', '', tagname)


class NodeWrapper(object):
  def __init__(self, name, attrib, items):
    self.name = name
    self.attrib = attrib
    self._list = []
    self._dict = {}
    for key, value in items:
      self._list.append((key, value))
      self._dict[key] = value

  def _Get(self, key):
    if isinstance(key, slice):
      return self._list[key]
    try:
      return self._dict[key]
    except KeyError, e:
      try:
        idx = int(key)
      except ValueError:
        pass
      else:
        return self._list[idx][1]
      raise e

  def get(self, key, defval=None):
    try:
      return self._Get(key)
    except KeyError:
      return defval

  def __getattr__(self, key):
    return self._Get(key)

  def __getitem__(self, key):
    return self._Get(key)

  def iteritems(self):
    return self._dict.iteritems()

  def __str__(self):
    out = []
    for key, value in self._list:
      value = str(value)
      if '\n' in value:
        value = '\n' + re.sub(re.compile(r'^', re.M), '  ', value)
      out.append('%s: %s' % (key, value))
    return '\n'.join(out)

  def __repr__(self):
    return str(self._list)


def _Parse(node):
  if node.text and node.text.strip():
    return node.text
  else:
    return NodeWrapper(_StripNamespace(node.tag), node.attrib,
                       [(_StripNamespace(sub.tag), _Parse(sub))
                        for sub in node])


def Parse(xmlstring):
  root = xml.etree.ElementTree.fromstring(xmlstring)
  return _Parse(root)


def main():
  with Envelope(1234, False) as xml:
    #print GetParameterNames(xml, 'System.', 1)
    ht.logger.info(GetParameterNames(xml, 'System.', 1))
  with Envelope(11, None) as xml:
    #print SetParameterValuesFault(
    #    xml,
    #    [('Object.x.y', CpeFault.INVALID_PARAM_TYPE, 'stupid error'),
    #     ('Object.y.z', CpeFault.INVALID_PARAM_NAME, 'blah error')])
    ht.logger.info(SetParameterValuesFault(
        xml,
        [('Object.x.y', CpeFault.INVALID_PARAM_TYPE, 'stupid error'),
         ('Object.y.z', CpeFault.INVALID_PARAM_NAME, 'blah error')]))
  parsed = Parse(str(xml))
  #print repr(parsed)
  #print parsed.Body
  #print parsed.Body.Fault.detail.Fault[2:4]
  ht.logger.info(repr(parsed))
  ht.logger.info(parsed.Body)
  ht.logger.info(parsed.Body.Fault.detail.Fault[2:4])
  with Envelope(12, None) as xml:
    #print SimpleFault(xml, CpeFault.DOWNLOAD_CORRUPTED, 'bad mojo')
    ht.logger.info(SimpleFault(xml, CpeFault.DOWNLOAD_CORRUPTED, 'bad mojo'))


if __name__ == '__main__':
  main()
