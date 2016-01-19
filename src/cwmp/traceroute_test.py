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

"""Unit tests for TraceRoute implementation."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import unittest
import google3
import tr.mainloop
import traceroute


class TraceRouteTest(unittest.TestCase):
  """Tests for traceroute.py."""

  def _DoTrace(self, loop, trace, hostname, maxhops):
    trace.Host = hostname
    trace.MaxHopCount = maxhops
    trace.DiagnosticsState = 'Requested'
    while trace.DiagnosticsState == 'Requested':
      loop.RunOnce(timeout=5)

  def testTraceRoute(self):
    loop = tr.mainloop.MainLoop()
    trace = traceroute.TraceRoute(loop)

    self._DoTrace(loop, trace, '127.0.0.1', 1)
    self.assertEqual(len(trace.RouteHopsList), 1)
    self.assertEqual(trace.RouteHopsList[1].Host, 'localhost')
    self.assertEqual(trace.RouteHopsList[1].HostAddress, '127.0.0.1')
    self.assertEqual(trace.DiagnosticsState, 'Error_MaxHopCountExceeded')

    self._DoTrace(loop, trace, '::1', 2)
    self.assertEqual(len(trace.RouteHopsList), 1)
    self.assertTrue(trace.RouteHopsList[1].Host == 'localhost' or
                    trace.RouteHopsList[1].Host == 'ip6-localhost')
    self.assertEqual(trace.RouteHopsList[1].HostAddress, '::1')
    self.assertEqual(trace.DiagnosticsState, 'Complete')

    self._DoTrace(loop, trace, 'this-name-does-not-exist', 30)
    self.assertEqual(len(trace.RouteHopsList), 0)
    self.assertEqual(trace.DiagnosticsState, 'Error_CannotResolveHostName')

    self._DoTrace(loop, trace, 'google.com', 30)
    self.assertTrue(len(trace.RouteHopsList) > 1)
    self.assertEqual(trace.DiagnosticsState, 'Complete')


if __name__ == '__main__':
  unittest.main()
