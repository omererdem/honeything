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

"""Unit tests for cwmpd."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import errno
import os
import select
import subprocess
import unittest
import google3
import tr.helpers


class RunserverTest(unittest.TestCase):
  """Tests for cwmpd and cwmp."""

  sockname = '/tmp/cwmpd_test.sock.%d' % os.getpid()

  def _StartClient(self, stdout=None):
    client = subprocess.Popen(['./cwmp', '--unix-path', self.sockname],
                              stdin=subprocess.PIPE, stdout=stdout)
    client.stdin.close()
    return client

  def _DoTest(self, args):
    print
    print 'Testing with args=%r' % args
    tr.helpers.Unlink(self.sockname)
    server = subprocess.Popen(['./cwmpd',
                               '--rcmd-port', '0',
                               '--unix-path', self.sockname,
                               '--close-stdio'] + args,
                              stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    try:
      print 'waiting for server to start...'
      while server.stdout.read():
        pass
      client = self._StartClient()
      self.assertEqual(client.wait(), 0)
      server.stdin.close()
      self.assertEqual(server.wait(), 0)
    finally:
      try:
        server.kill()
      except OSError:
        pass
      tr.helpers.Unlink(self.sockname)

  def testExitOnError(self):
    print 'testing client exit when server not running'
    client = self._StartClient(stdout=subprocess.PIPE)
    r, _, _ = select.select([client.stdout], [], [], 5)
    try:
      self.assertNotEqual(r, [])
      self.assertNotEqual(client.wait(), 0)
    finally:
      if client.poll() is None:
        client.kill()

  def testRunserver(self):
    self._DoTest(['--no-cpe'])
    self._DoTest(['--no-cpe',
                  '--platform', 'fakecpe'])
    self._DoTest(['--fake-acs',
                  '--platform', 'fakecpe'])


if __name__ == '__main__':
  unittest.main()
