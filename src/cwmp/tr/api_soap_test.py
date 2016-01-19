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

# unittest requires method names starting in 'test'
#pylint: disable-msg=C6409

"""Unit tests for api_soap.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime
import unittest
import xml.etree.ElementTree as ET

import google3
import api_soap


expectedTransferComplete = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:cwmp="urn:dslforum-org:cwmp-1-2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soap-enc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header>
  </soap:Header>
  <soap:Body>
    <cwmp:TransferComplete>
      <CommandKey>cmdkey</CommandKey>
      <FaultStruct>
        <FaultCode>123</FaultCode>
        <FaultString>faultstring</FaultString>
      </FaultStruct>
      <StartTime>2011-12-05T12:01:02Z</StartTime>
      <CompleteTime>2011-12-05T12:01:03Z</CompleteTime>
    </cwmp:TransferComplete>
  </soap:Body>
</soap:Envelope>"""


SOAPNS = '{http://schemas.xmlsoap.org/soap/envelope/}'
CWMPNS = '{urn:dslforum-org:cwmp-1-2}'


class RpcMessageTest(unittest.TestCase):
  """Tests for formatting of XML objects."""

  def testTransferComplete(self):
    encode = api_soap.Encode()
    start = datetime.datetime(2011, 12, 5, 12, 01, 02)
    end = datetime.datetime(2011, 12, 5, 12, 01, 03)
    xml = str(encode.TransferComplete('cmdkey', 123, 'faultstring', start, end))

    root = ET.fromstring(str(xml))
    xfer = root.find(SOAPNS + 'Body/' + CWMPNS + 'TransferComplete')
    self.assertTrue(xfer)
    self.assertEqual(xfer.find('CommandKey').text, 'cmdkey')
    self.assertEqual(xfer.find('FaultStruct/FaultCode').text, '123')
    self.assertEqual(xfer.find('FaultStruct/FaultString').text, 'faultstring')
    self.assertTrue(xfer.find('StartTime').text)
    self.assertTrue(xfer.find('CompleteTime').text)


class ApiSoapTest(unittest.TestCase):
  """Tests for methods in api_soap.py."""

  class ThisHasXsiType(object):
    xsitype = 'xsd:foo'
    def __str__(self):
      return 'foo'

  def testSoapify(self):
    tobj = self.ThisHasXsiType()
    self.assertEqual(api_soap.Soapify(tobj), ('xsd:foo', 'foo'))
    self.assertEqual(api_soap.Soapify(True), ('xsd:boolean', '1'))
    self.assertEqual(api_soap.Soapify(False), ('xsd:boolean', '0'))
    self.assertEqual(api_soap.Soapify(100), ('xsd:unsignedInt', '100'))
    self.assertEqual(api_soap.Soapify(3.14159), ('xsd:double', '3.14159'))
    dt = datetime.datetime(1999, 12, 31, 23, 59, 58, 999999)
    self.assertEqual(api_soap.Soapify(dt), ('xsd:dateTime', '1999-12-31T23:59:58.999999Z'))
    dt2 = datetime.datetime(1999, 12, 31, 23, 59, 58)
    self.assertEqual(api_soap.Soapify(dt2), ('xsd:dateTime', '1999-12-31T23:59:58Z'))


if __name__ == '__main__':
  unittest.main()
