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

"""Implementation of tr-181 Device.DeviceInfo.TemperatureStatus object.

Handles the Device.DeviceInfo.TemperatureStatus portion of TR-181, as
described by http://www.broadband-forum.org/cwmp/tr-181-2-2-0.html
"""

__author__ = 'dgentry@google.com (Denton Gentry)'

import copy
import datetime
import re
import subprocess
import tornado.ioloop
import tr.core
import tr.cwmpbool
import tr.cwmpdate
import tr.tr181_v2_2
import tr.x_catawampus_tr181_2_0

BASE181TEMPERATURE = tr.tr181_v2_2.Device_v2_2.DeviceInfo.TemperatureStatus
CATA181DI = tr.x_catawampus_tr181_2_0.X_CATAWAMPUS_ORG_Device_v2_0.DeviceInfo
NUMBER = re.compile(r'(\d+(?:\.\d+)?)')

# tr-181 defines a temperature below 0 Kelvin as "Invalid temperature"
BADCELSIUS = -274

# Unit tests can override these with fake data
HDPARM = 'hdparm'
PERIODICCALL = tornado.ioloop.PeriodicCallback
TIMENOW = datetime.datetime.now


def GetNumberFromFile(filename):
  """Extract a number from a file.

  The number can be an integer or float. If float, it will be rounded.

  Returns:
    an integer.
  """
  with open(filename, 'r') as f:
    result = NUMBER.search(f.readline())
    if result is not None:
      return int(round(float(result.group(0))))
  raise ValueError('No number found in %s' % filename)


class TemperatureSensorConfig(object):
  pass


class TemperatureSensor(BASE181TEMPERATURE.TemperatureSensor):
  """Implements tr-181 TemperatureStatus.TemperatureSensor.

     Args:
       name: a descriptive name for this sensor.
       sensor: an object with a GetTemperature() method.

     This class implements the hardware and platform-independant portions
     of a TemperatureSensor. It periodically calls sensor.GetTemperature()
     to obtain a sample from the hardware.
  """

  DEFAULTPOLL = 300

  def __init__(self, name, sensor, ioloop=None):
    super(TemperatureSensor, self).__init__()
    self._name = name
    self._sensor = sensor
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.scheduler = None

    self.config = self._GetDefaultSettings()
    self.old_config = None
    self._ResetReadings()
    self._Configure()

  def _ResetReadings(self):
    unknown_time = tr.cwmpdate.format(0)
    self._high_alarm_time = unknown_time
    self._do_reset_high_alarm_time = False
    self._low_alarm_time = unknown_time
    self._do_reset_low_alarm_time = False
    self._last_update = unknown_time
    self._min_value = None
    self._min_time = unknown_time
    self._max_value = None
    self._max_time = unknown_time
    self._reset_time = unknown_time
    self._value = BADCELSIUS

  def _GetDefaultSettings(self):
    obj = TemperatureSensorConfig()
    obj.p_enable = True
    obj.p_polling_interval = self.DEFAULTPOLL
    obj.p_low_alarm_value = None
    obj.p_high_alarm_value = None
    return obj

  def StartTransaction(self):
    self.old_config = self.config
    self.config = copy.deepcopy(self.old_config)

  def AbandonTransaction(self):
    self.config = self.old_config
    self.old_config = None

  def CommitTransaction(self):
    self.old_config = None
    self._Configure()

  def GetEnable(self):
    return self.config.p_enable

  def SetEnable(self, value):
    self.config.p_enable = tr.cwmpbool.parse(value)

  Enable = property(GetEnable, SetEnable, None, 'TemperatureSensor.Enable')

  def GetHighAlarmValue(self):
    if self.config.p_high_alarm_value is None:
      return BADCELSIUS
    else:
      return self.config.p_high_alarm_value

  def SetHighAlarmValue(self, value):
    self.config.p_high_alarm_value = int(value)
    self._do_reset_high_alarm_time = True

  HighAlarmValue = property(GetHighAlarmValue, SetHighAlarmValue, None,
                            'TemperatureSensor.HighAlarmValue')

  @property
  def HighAlarmTime(self):
    return self._high_alarm_time

  @property
  def LastUpdate(self):
    return self._last_update

  def GetLowAlarmValue(self):
    if self.config.p_low_alarm_value is None:
      return BADCELSIUS
    else:
      return self.config.p_low_alarm_value

  def SetLowAlarmValue(self, value):
    self.config.p_low_alarm_value = int(value)
    self._do_reset_low_alarm_time = True

  LowAlarmValue = property(GetLowAlarmValue, SetLowAlarmValue, None,
                           'TemperatureSensor.LowAlarmValue')

  @property
  def LowAlarmTime(self):
    return self._low_alarm_time

  @property
  def MinTime(self):
    return self._min_time

  @property
  def MinValue(self):
    return BADCELSIUS if self._min_value is None else self._min_value

  @property
  def MaxTime(self):
    return self._max_time

  @property
  def MaxValue(self):
    return BADCELSIUS if self._max_value is None else self._max_value

  @property
  def Name(self):
    return self._name

  def GetPollingInterval(self):
    return self.config.p_polling_interval

  def SetPollingInterval(self, value):
    v = int(value)
    if v < 0:
      raise ValueError('Invalid PollingInterval %d' % v)
    if v == 0:
      v = self.DEFAULTPOLL
    self.config.p_polling_interval = v

  PollingInterval = property(GetPollingInterval, SetPollingInterval)

  def GetReset(self):
    return False

  def SetReset(self, value):
    if tr.cwmpbool.parse(value):
      self._ResetReadings()
      self._reset_time = tr.cwmpdate.format(TIMENOW())

  Reset = property(GetReset, SetReset, None, 'TemperatureSensor.Reset')

  @property
  def ResetTime(self):
    return self._reset_time

  @property
  def Status(self):
    return 'Enabled' if self.config.p_enable else 'Disabled'

  @property
  def Value(self):
    return self._value

  def SampleTemperature(self):
    t = self._sensor.GetTemperature()
    self._value = t
    now = tr.cwmpdate.format(TIMENOW())
    self._last_update = now
    if self._min_value is None or t < self._min_value:
      self._min_value = t
      self._min_time = now
    if self._max_value is None or t > self._max_value:
      self._max_value = t
      self._max_time = now
    high = self.config.p_high_alarm_value
    if high is not None and t > high:
      self._high_alarm_time = now
    low = self.config.p_low_alarm_value
    if low is not None and t < low:
      self._low_alarm_time = now

  def _Configure(self):
    if self._do_reset_high_alarm_time:
      self._high_alarm_time = tr.cwmpdate.format(0)
      self._do_reset_high_alarm_time = False
    if self._do_reset_low_alarm_time:
      self._low_alarm_time = tr.cwmpdate.format(0)
      self._do_reset_low_alarm_time = False
    if self.scheduler is not None:
      self.scheduler.stop()
      self.scheduler = None
    if self.config.p_enable:
      self.scheduler = PERIODICCALL(self.SampleTemperature,
              self.config.p_polling_interval * 1000, io_loop=self.ioloop)
      self.scheduler.start()
    # Let new alarm thresholds take effect
    self.SampleTemperature()


class SensorHdparm(object):
  """Hard drive temperature sensor implementation.

     This object can be passed as the sensor argument to a
     TemperatureSensor object, to monitor hard drive temperature.
  """

  DRIVETEMP = re.compile(r'drive temperature \(celsius\) is:\s*(\d+(?:\.\d+)?)')

  def __init__(self, dev):
    self._dev = dev if dev[0] == '/' else '/dev/' + dev

  def GetTemperature(self):
    hd = subprocess.Popen([HDPARM, '-H', self._dev], stdout=subprocess.PIPE)
    out, _ = hd.communicate(None)
    for line in out.splitlines():
      result = self.DRIVETEMP.search(line)
      if result is not None:
        return int(round(float(result.group(1))))
    return BADCELSIUS


class SensorReadFromFile(object):
  """Read a temperature from an arbitrary file.

     Opens a file looks for a number in the first line.
     This is treated as a temperature in degrees Celsius.

     This object can be passed as the sensor argument to a
     TemperatureSensor object, to monitor an arbitrary
     temperature written to a file.
  """

  def __init__(self, filename):
    self._filename = filename

  def GetTemperature(self):
    try:
      return GetNumberFromFile(self._filename)
    except (IOError, ValueError):
      print 'TempFromFile %s: bad value' % self._filename
      return BADCELSIUS


class TemperatureStatus(CATA181DI.TemperatureStatus):
  """Implementation of tr-181 DeviceInfo.TemperatureStatus."""

  def __init__(self):
    super(TemperatureStatus, self).__init__()
    self.TemperatureSensorList = dict()
    self._next_sensor_number = 1
    self.X_CATAWAMPUS_ORG_FanList = dict()
    self._next_fan_number = 1

  @property
  def TemperatureSensorNumberOfEntries(self):
    return len(self.TemperatureSensorList)

  @property
  def X_CATAWAMPUS_ORG_FanNumberOfEntries(self):
    return len(self.X_CATAWAMPUS_ORG_FanList)

  def AddSensor(self, name, sensor):
    ts = TemperatureSensor(name=name, sensor=sensor)
    ts.SampleTemperature()
    self.TemperatureSensorList[self._next_sensor_number] = ts
    self._next_sensor_number += 1

  def AddFan(self, fan):
    self.X_CATAWAMPUS_ORG_FanList[self._next_fan_number] = fan
    self._next_fan_number += 1


class FanReadFileRPS(CATA181DI.TemperatureStatus.X_CATAWAMPUS_ORG_Fan):
  """Implementation of Fan object, reading rev/sec from a file."""

  def __init__(self, name, filename):
    super(FanReadFileRPS, self).__init__()
    self._name = name
    self._filename = filename

  @property
  def Name(self):
    return self._name

  @property
  def RPM(self):
    try:
      rps = GetNumberFromFile(self._filename)
      return rps * 60
    except ValueError as e:
      print 'FanReadFileRPS bad value %s' % self._filename
      return -1

  @property
  def DesiredRPM(self):
    return -1

  @property
  def DesiredPercentage(self):
    return -1

def main():
  pass


if __name__ == '__main__':
  main()
