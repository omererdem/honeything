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

"""Unit tests for tr-181 DeviceInfo.TemperatureStatus implementation."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime
import os
import unittest

import google3
import tr.core
import temperature


TR181_BAD_TEMPERATURE = -274


class MockSensor(object):
  def __init__(self):
    self.temperature = 0.0

  def GetTemperature(self):
    return self.temperature


class MockTime(object):
  TIME = 1341359845.764075

  @staticmethod
  def MockTimeNow():
    return datetime.datetime.utcfromtimestamp(MockTime.TIME)


fake_periodics = []
class FakePeriodicCallback(object):
  def __init__(self, callback, callback_time, io_loop=None):
    self.callback = callback
    self.callback_time = callback_time / 1000
    self.io_loop = io_loop
    self.start_called = False
    self.stop_called = False
    fake_periodics.append(self)

  def start(self):
    self.start_called = True

  def stop(self):
    self.stop_called = True


class TemperatureTest(unittest.TestCase):
  """Tests for temperature.py."""

  def setUp(self):
    self.old_HDPARM = temperature.HDPARM
    self.old_PERIODICCALL = temperature.PERIODICCALL
    self.old_TIMENOW = temperature.TIMENOW
    temperature.HDPARM = 'testdata/temperature/hdparm-H'

  def tearDown(self):
    temperature.HDPARM = self.old_HDPARM
    temperature.PERIODICCALL = self.old_PERIODICCALL
    temperature.TIMENOW = self.old_TIMENOW

  def testHardDriveTemperature(self):
    hd = temperature.SensorHdparm('sda')
    self.assertEqual(hd.GetTemperature(), 50)
    hd = temperature.SensorHdparm('/dev/sda')
    self.assertEqual(hd.GetTemperature(), 50)

  def testTemperatureFromFile(self):
    t = temperature.SensorReadFromFile('testdata/temperature/file1')
    self.assertEqual(t.GetTemperature(), 72)
    t = temperature.SensorReadFromFile('testdata/temperature/file2')
    self.assertEqual(t.GetTemperature(), 73)
    t = temperature.SensorReadFromFile('testdata/temperature/file3')
    self.assertEqual(t.GetTemperature(), 74)
    t = temperature.SensorReadFromFile('testdata/temperature/file4')
    self.assertEqual(t.GetTemperature(), TR181_BAD_TEMPERATURE)
    t = temperature.SensorReadFromFile('no/such/file')
    self.assertEqual(t.GetTemperature(), TR181_BAD_TEMPERATURE)

  def testValidateExports(self):
    t = temperature.TemperatureSensor(name='TestTemp', sensor=MockSensor())
    t.ValidateExports()
    fan = temperature.FanReadFileRPS('Fan1', 'testdata/temperature/file1')
    fan.ValidateExports()

  def testDefaults(self):
    sensor = MockSensor()
    sensor.temperature = TR181_BAD_TEMPERATURE

    t = temperature.TemperatureSensor(name='TestTemp', sensor=sensor)
    t.Reset = True
    self.assertTrue(t.Enable)
    self.assertEqual(t.HighAlarmValue, TR181_BAD_TEMPERATURE)
    self.assertEqual(t.HighAlarmTime, '0001-01-01T00:00:00Z')
    self.assertEqual(t.LowAlarmValue, TR181_BAD_TEMPERATURE)
    self.assertEqual(t.LowAlarmTime, '0001-01-01T00:00:00Z')
    self.assertEqual(t.MinValue, TR181_BAD_TEMPERATURE)
    self.assertEqual(t.MinTime, '0001-01-01T00:00:00Z')
    self.assertEqual(t.MaxValue, TR181_BAD_TEMPERATURE)
    self.assertEqual(t.MaxTime, '0001-01-01T00:00:00Z')
    self.assertEqual(t.LastUpdate, '0001-01-01T00:00:00Z')
    self.assertEqual(t.PollingInterval, 300)
    self.assertFalse(t.Reset)
    self.assertEqual(t.Status, 'Enabled')
    self.assertEqual(t.Value, TR181_BAD_TEMPERATURE)

  def testMinMax(self):
    temperature.TIMENOW = MockTime.MockTimeNow
    sensor = MockSensor()
    sensor.temperature = TR181_BAD_TEMPERATURE

    t = temperature.TemperatureSensor(name='TestTemp', sensor=sensor)
    t.Reset = True
    self.assertEqual(t.MaxTime, '0001-01-01T00:00:00Z')
    self.assertEqual(t.MaxValue, TR181_BAD_TEMPERATURE)
    self.assertEqual(t.MinTime, '0001-01-01T00:00:00Z')
    self.assertEqual(t.MinValue, TR181_BAD_TEMPERATURE)
    self.assertEqual(t.Value, TR181_BAD_TEMPERATURE)

    sensor.temperature = 90.0
    MockTime.TIME = 1341359845.0
    t.SampleTemperature()
    self.assertEqual(t.MaxTime, '2012-07-03T23:57:25Z')
    self.assertEqual(t.MaxValue, 90)
    self.assertEqual(t.MinTime, '2012-07-03T23:57:25Z')
    self.assertEqual(t.MinValue, 90)
    self.assertEqual(t.Value, 90)

    sensor.temperature = 110.0
    MockTime.TIME = 1341359846
    t.SampleTemperature()
    self.assertEqual(t.MaxTime, '2012-07-03T23:57:26Z')
    self.assertEqual(t.MaxValue, 110)
    self.assertEqual(t.MinTime, '2012-07-03T23:57:25Z')
    self.assertEqual(t.MinValue, 90)
    self.assertEqual(t.Value, 110)

    sensor.temperature = 80.0
    MockTime.TIME = 1341359847
    t.SampleTemperature()
    self.assertEqual(t.MaxTime, '2012-07-03T23:57:26Z')
    self.assertEqual(t.MaxValue, 110)
    self.assertEqual(t.MinTime, '2012-07-03T23:57:27Z')
    self.assertEqual(t.MinValue, 80)
    self.assertEqual(t.Value, 80)

    t.Reset = True
    self.assertEqual(t.MaxTime, '0001-01-01T00:00:00Z')
    self.assertEqual(t.MaxValue, TR181_BAD_TEMPERATURE)
    self.assertEqual(t.MinTime, '0001-01-01T00:00:00Z')
    self.assertEqual(t.MinValue, TR181_BAD_TEMPERATURE)
    self.assertEqual(t.Value, TR181_BAD_TEMPERATURE)

  def testAlarms(self):
    temperature.TIMENOW = MockTime.MockTimeNow
    sensor = MockSensor()

    t = temperature.TemperatureSensor(name='TestTemp', sensor=sensor)
    self.assertEqual(t.HighAlarmValue, TR181_BAD_TEMPERATURE)
    self.assertEqual(t.HighAlarmTime, '0001-01-01T00:00:00Z')
    self.assertEqual(t.LowAlarmValue, TR181_BAD_TEMPERATURE)
    self.assertEqual(t.LowAlarmTime, '0001-01-01T00:00:00Z')

    t.HighAlarmValue = 100
    t.LowAlarmValue = 50

    sensor.temperature = 90.0
    t.SampleTemperature()
    self.assertEqual(t.HighAlarmValue, 100)
    self.assertEqual(t.HighAlarmTime, '0001-01-01T00:00:00Z')
    self.assertEqual(t.LowAlarmValue, 50)
    self.assertEqual(t.LowAlarmTime, '0001-01-01T00:00:00Z')

    sensor.temperature = 110.0
    MockTime.TIME = 1341359848
    t.SampleTemperature()
    self.assertEqual(t.HighAlarmTime, '2012-07-03T23:57:28Z')
    self.assertEqual(t.LowAlarmTime, '0001-01-01T00:00:00Z')

    sensor.temperature = 40.0
    MockTime.TIME = 1341359849
    t.SampleTemperature()
    self.assertEqual(t.HighAlarmTime, '2012-07-03T23:57:28Z')
    self.assertEqual(t.LowAlarmTime, '2012-07-03T23:57:29Z')

    t.Reset = True
    self.assertEqual(t.HighAlarmValue, 100)
    self.assertEqual(t.HighAlarmTime, '0001-01-01T00:00:00Z')
    self.assertEqual(t.LowAlarmValue, 50)
    self.assertEqual(t.LowAlarmTime, '0001-01-01T00:00:00Z')

  def testPeriodicCallback(self):
    del fake_periodics[:]
    temperature.PERIODICCALL = FakePeriodicCallback
    t = temperature.TemperatureSensor(name='TestTemp', sensor=MockSensor())
    self.assertTrue(t.Enable)
    self.assertEqual(len(fake_periodics), 1)
    self.assertTrue(fake_periodics[0].start_called)
    self.assertFalse(fake_periodics[0].stop_called)
    self.assertEqual(fake_periodics[0].callback_time, 300)
    self.assertEqual(t.Status, 'Enabled')

    t.StartTransaction()
    t.Enable = False
    t.CommitTransaction()
    self.assertEqual(t.Status, 'Disabled')
    self.assertTrue(fake_periodics[0].stop_called)

    t.StartTransaction()
    t.Enable = True
    t.PollingInterval = 400
    t.CommitTransaction()

    self.assertEqual(len(fake_periodics), 2)
    self.assertTrue(fake_periodics[1].start_called)
    self.assertFalse(fake_periodics[1].stop_called)
    self.assertEqual(fake_periodics[1].callback_time, 400)

    del fake_periodics[0:1]

  def testTemperatureStatus(self):
    ts = temperature.TemperatureStatus()
    ts.AddSensor(name='Test1', sensor=MockSensor())
    ts.AddSensor(name='Test2', sensor=MockSensor())
    ts.ValidateExports()
    self.assertEqual(ts.TemperatureSensorNumberOfEntries, 2)
    self.assertEqual(ts.TemperatureSensorList[1].Name, 'Test1')
    self.assertEqual(ts.TemperatureSensorList[2].Name, 'Test2')

  def testFanRPS(self):
    fan = temperature.FanReadFileRPS('Fan1', 'testdata/temperature/file1')
    self.assertEqual(fan.Name, 'Fan1')
    self.assertEqual(fan.RPM, 4320)
    self.assertEqual(fan.DesiredRPM, -1)
    self.assertEqual(fan.DesiredPercentage, -1)
    fan = temperature.FanReadFileRPS('Fan2', 'testdata/temperature/file2')
    self.assertEqual(fan.Name, 'Fan2')
    self.assertEqual(fan.RPM, 4380)
    self.assertEqual(fan.DesiredRPM, -1)
    self.assertEqual(fan.DesiredPercentage, -1)
    fan = temperature.FanReadFileRPS('Fan3', 'testdata/temperature/file3')
    self.assertEqual(fan.Name, 'Fan3')
    self.assertEqual(fan.RPM, 4440)
    self.assertEqual(fan.DesiredRPM, -1)
    self.assertEqual(fan.DesiredPercentage, -1)
    fan = temperature.FanReadFileRPS('Fan4', 'testdata/temperature/file4')
    self.assertEqual(fan.Name, 'Fan4')
    self.assertTrue(fan.RPM < 0)
    self.assertEqual(fan.DesiredRPM, -1)
    self.assertEqual(fan.DesiredPercentage, -1)


if __name__ == '__main__':
  unittest.main()
