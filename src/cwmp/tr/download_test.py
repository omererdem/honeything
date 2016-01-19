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

"""Unit tests for download.py."""

__author__ = 'dgentry@google.com (Denton Gentry)'

import datetime
import shutil
import tempfile
import time
import unittest

import google3
import core
import download
import persistobj


mock_http_clients = []
mock_http_downloads = []
mock_installers = []
mock_downloads = []


class MockHttpClient(object):
  def __init__(self, io_loop=None):
    self.did_fetch = False
    self.request = None
    self.callback = None
    mock_http_clients.append(self)

  def fetch(self, request, callback):
    self.did_fetch = True
    self.request = request
    self.callback = callback


class MockIoloop(object):
  def __init__(self):
    self.timeout = None
    self.callback = None

  def add_timeout(self, timeout, callback, monotonic=None):
    self.timeout = timeout
    self.callback = callback


class MockHttpDownload(object):
  def __init__(self, url, username=None, password=None,
               download_complete_cb=None, download_dir=None, ioloop=None):
    self.url = url
    self.username = username
    self.password = password
    self.download_complete_cb = download_complete_cb
    self.download_dir = download_dir
    self.ioloop = ioloop
    self.did_fetch = False
    mock_http_downloads.append(self)

  def fetch(self):
    self.did_fetch = True


class MockInstaller(object):
  def __init__(self, filename):
    self.filename = filename
    self.did_install = False
    self.did_reboot = False
    self.file_type = None
    self.targe_filename = None
    self.install_callback = None
    mock_installers.append(self)

  def install(self, file_type, target_filename, callback):
    self.did_install = True
    self.file_type = file_type
    self.target_filename = target_filename
    self.install_callback = callback
    return True

  def reboot(self):
    self.did_reboot = True


class MockTransferComplete(object):
  def __init__(self):
    self.transfer_complete_called = False
    self.dl = None
    self.command_key = None
    self.faultcode = None
    self.faultstring = None
    self.starttime = None
    self.endtime = None

  def SendTransferComplete(self, dl, command_key, faultcode, faultstring,
                           starttime, endtime, event_code):
    self.transfer_complete_called = True
    self.dl = dl
    self.command_key = command_key
    self.faultcode = faultcode
    self.faultstring = faultstring
    self.starttime = starttime
    self.endtime = endtime
    self.event_code = event_code


class MockFile(object):
  def __init__(self, name):
    self.name = name


def _Delta(t):
  return datetime.timedelta(seconds=t)


class DownloadTest(unittest.TestCase):
  def setUp(self):
    self.tmpdir = tempfile.mkdtemp()
    download.INSTALLER = MockInstaller
    self.done_command_key = None
    self.old_time = time.time
    del mock_installers[:]
    del mock_http_downloads[:]
    download.DOWNLOAD_CLIENT['http'] = MockHttpDownload
    download.DOWNLOAD_CLIENT['https'] = MockHttpDownload

  def tearDown(self):
    time.time = self.old_time
    shutil.rmtree(self.tmpdir)
    del mock_installers[:]
    del mock_http_clients[:]

  def mockTime(self):
    return 123456.0

  def QCheckBoring(self, dl, args):
    """Check get_queue_state() fields which don't change, and return qstate."""
    q = dl.get_queue_state()
    self.assertEqual(q.CommandKey, args['command_key'])
    self.assertTrue(q.IsDownload)
    self.assertEqual(q.FileType, args['file_type'])
    self.assertEqual(q.FileSize, args['file_size'])
    self.assertEqual(q.TargetFileName, args['target_filename'])
    return q.State

  def testSuccess(self):
    ioloop = MockIoloop()
    cmpl = MockTransferComplete()
    time.time = self.mockTime

    kwargs = dict(command_key='testCommandKey',
                  file_type='testFileType',
                  url='http://example.com/foo',
                  username='testUsername',
                  password='testPassword',
                  file_size=1000,
                  target_filename='testTargetFilename',
                  delay_seconds=99)
    stateobj = persistobj.PersistentObject(objdir=self.tmpdir,
                                           rootname='testObj',
                                           filename=None, **kwargs)

    dl = download.Download(stateobj=stateobj,
                           transfer_complete_cb=cmpl.SendTransferComplete,
                           ioloop=ioloop)
    self.assertEqual(self.QCheckBoring(dl, kwargs), 1)  # 1: Not Yet Started

    # Step 1: Wait delay_seconds
    dl.do_start()
    self.assertEqual(ioloop.timeout, _Delta(kwargs['delay_seconds']))
    self.assertEqual(self.QCheckBoring(dl, kwargs), 1)  # 1: Not Yet Started

    # Step 2: HTTP Download
    dl.timer_callback()
    self.assertEqual(len(mock_http_downloads), 1)
    http = mock_http_downloads[0]
    self.assertEqual(http.url, kwargs['url'])
    self.assertEqual(http.username, kwargs['username'])
    self.assertEqual(http.password, kwargs['password'])
    self.assertTrue(http.download_complete_cb)
    self.assertTrue(http.did_fetch)
    self.assertEqual(self.QCheckBoring(dl, kwargs), 2)  # 2: In process

    # Step 3: Install
    dlfile = MockFile('/path/to/downloaded/file')
    http.download_complete_cb(0, '', dlfile)
    self.assertEqual(len(mock_installers), 1)
    inst = mock_installers[0]
    self.assertTrue(inst.did_install)
    self.assertEqual(inst.file_type, kwargs['file_type'])
    self.assertEqual(inst.target_filename, kwargs['target_filename'])
    self.assertEqual(inst.filename, dlfile.name)
    self.assertFalse(inst.did_reboot)
    self.assertEqual(self.QCheckBoring(dl, kwargs), 2)  # 2: In process

    # Step 4: Reboot
    inst.install_callback(0, '', must_reboot=True)
    self.assertTrue(inst.did_reboot)
    self.assertEqual(self.QCheckBoring(dl, kwargs), 2)  # 2: In process

    # Step 5: Send Transfer Complete
    dl.reboot_callback(0, '')
    self.assertTrue(cmpl.transfer_complete_called)
    self.assertEqual(cmpl.command_key, kwargs['command_key'])
    self.assertEqual(cmpl.faultcode, 0)
    self.assertEqual(cmpl.faultstring, '')
    self.assertEqual(cmpl.starttime, self.mockTime())
    self.assertEqual(cmpl.endtime, self.mockTime())
    self.assertEqual(cmpl.event_code, 'M Download')
    self.assertEqual(self.QCheckBoring(dl, kwargs), 3)  # 3: Cleaning up

    # Step 6: Wait for Transfer Complete Response
    self.assertFalse(dl.cleanup())
    self.assertEqual(self.QCheckBoring(dl, kwargs), 3)  # 3: Cleaning up

  def testDownloadFailed(self):
    ioloop = MockIoloop()
    cmpl = MockTransferComplete()
    time.time = self.mockTime

    kwargs = dict(command_key='testCommandKey',
                  url='http://example.com/foo',
                  delay_seconds=1)
    stateobj = persistobj.PersistentObject(objdir=self.tmpdir,
                                           rootname='testObj',
                                           filename=None, **kwargs)

    dl = download.Download(stateobj=stateobj,
                           transfer_complete_cb=cmpl.SendTransferComplete,
                           ioloop=ioloop)

    # Step 1: Wait delay_seconds
    dl.do_start()
    self.assertEqual(ioloop.timeout, _Delta(kwargs['delay_seconds']))

    # Step 2: HTTP Download
    dl.timer_callback()
    self.assertEqual(len(mock_http_downloads), 1)
    http = mock_http_downloads[0]
    self.assertEqual(http.url, kwargs['url'])

    # Step 3: Download fails
    http.download_complete_cb(100, 'TestDownloadError', None)
    self.assertEqual(len(mock_installers), 0)
    self.assertTrue(cmpl.transfer_complete_called)
    self.assertEqual(cmpl.command_key, kwargs['command_key'])
    self.assertEqual(cmpl.faultcode, 100)
    self.assertEqual(cmpl.faultstring, 'TestDownloadError')
    self.assertEqual(cmpl.starttime, 0.0)
    self.assertEqual(cmpl.endtime, 0.0)
    self.assertEqual(cmpl.event_code, 'M Download')

  def testInstallFailed(self):
    ioloop = MockIoloop()
    cmpl = MockTransferComplete()
    time.time = self.mockTime

    kwargs = dict(command_key='testCommandKey',
                  url='http://example.com/foo',
                  delay_seconds=1)
    stateobj = persistobj.PersistentObject(objdir=self.tmpdir,
                                           rootname='testObj',
                                           filename=None, **kwargs)

    dl = download.Download(stateobj=stateobj,
                           transfer_complete_cb=cmpl.SendTransferComplete,
                           ioloop=ioloop)

    # Step 1: Wait delay_seconds
    dl.do_start()
    self.assertEqual(ioloop.timeout, _Delta(kwargs['delay_seconds']))

    # Step 2: HTTP Download
    dl.timer_callback()
    self.assertEqual(len(mock_http_downloads), 1)
    http = mock_http_downloads[0]
    self.assertEqual(http.url, kwargs['url'])

    # Step 3: Install
    dlfile = MockFile('/path/to/downloaded/file')
    http.download_complete_cb(0, '', dlfile)
    self.assertEqual(len(mock_installers), 1)
    inst = mock_installers[0]
    self.assertTrue(inst.did_install)
    self.assertEqual(inst.filename, dlfile.name)
    self.assertFalse(inst.did_reboot)

    # Step 4: Install Failed
    inst.install_callback(101, 'TestInstallError', must_reboot=False)
    self.assertTrue(cmpl.transfer_complete_called)
    self.assertEqual(cmpl.command_key, kwargs['command_key'])
    self.assertEqual(cmpl.faultcode, 101)
    self.assertEqual(cmpl.faultstring, 'TestInstallError')
    self.assertEqual(cmpl.starttime, 0.0)
    self.assertEqual(cmpl.endtime, 0.0)
    self.assertEqual(cmpl.event_code, 'M Download')

  def testInstallNoReboot(self):
    ioloop = MockIoloop()
    cmpl = MockTransferComplete()
    time.time = self.mockTime

    kwargs = dict(command_key='testCommandKey',
                  url='http://example.com/foo',
                  delay_seconds=1)
    stateobj = persistobj.PersistentObject(objdir=self.tmpdir,
                                           rootname='testObj',
                                           filename=None, **kwargs)

    dl = download.Download(stateobj=stateobj,
                           transfer_complete_cb=cmpl.SendTransferComplete,
                           ioloop=ioloop)

    # Step 1: Wait delay_seconds
    dl.do_start()
    self.assertEqual(ioloop.timeout, _Delta(kwargs['delay_seconds']))

    # Step 2: HTTP Download
    dl.timer_callback()
    self.assertEqual(len(mock_http_downloads), 1)
    http = mock_http_downloads[0]
    self.assertEqual(http.url, kwargs['url'])

    # Step 3: Install
    dlfile = MockFile('/path/to/downloaded/file')
    http.download_complete_cb(0, '', dlfile)
    self.assertEqual(len(mock_installers), 1)
    inst = mock_installers[0]
    self.assertTrue(inst.did_install)
    self.assertEqual(inst.filename, dlfile.name)
    self.assertFalse(inst.did_reboot)

    # Step 4: Install Succeeded, no reboot
    inst.install_callback(0, '', must_reboot=False)
    self.assertTrue(cmpl.transfer_complete_called)
    self.assertEqual(cmpl.command_key, kwargs['command_key'])
    self.assertEqual(cmpl.faultcode, 0)
    self.assertEqual(cmpl.faultstring, '')
    self.assertEqual(cmpl.starttime, self.mockTime())
    self.assertEqual(cmpl.endtime, self.mockTime())
    self.assertEqual(cmpl.event_code, 'M Download')

  def testCancelRefused(self):
    ioloop = MockIoloop()
    cmpl = MockTransferComplete()

    kwargs = dict(command_key='testCommandKey',
                  url='http://example.com/foo')
    stateobj = persistobj.PersistentObject(objdir=self.tmpdir,
                                           rootname='testObj',
                                           filename=None, **kwargs)
    dl = download.Download(stateobj=stateobj,
                           transfer_complete_cb=cmpl.SendTransferComplete,
                           ioloop=ioloop)
    dl.do_start()  # Step 1: Wait delay_seconds
    dl.timer_callback()  # Step 2: HTTP Download
    dl.download_complete_callback(0, None, None)  # Step 3: Install
    self.assertTrue(dl.cleanup())
    dl.installer_callback(0, None, must_reboot=True)  # Step 4: Reboot
    self.assertTrue(dl.cleanup())
    dl.reboot_callback(0, '')  # Step 5: Rebooted
    self.assertFalse(dl.cleanup())

  def testCommandKey(self):
    kwargs = dict(command_key='testCommandKey')
    stateobj = persistobj.PersistentObject(objdir=self.tmpdir,
                                           rootname='testObj',
                                           filename=None, **kwargs)
    dl = download.Download(stateobj=stateobj, transfer_complete_cb=None)
    self.assertEqual(dl.CommandKey(), kwargs['command_key'])

    kwargs = dict()
    stateobj = persistobj.PersistentObject(objdir=self.tmpdir,
                                           rootname='testObj',
                                           filename=None, **kwargs)
    dl = download.Download(stateobj=stateobj, transfer_complete_cb=None)
    self.assertEqual(dl.CommandKey(), None)


class MockDownloadObj(object):
  def __init__(self, stateobj, transfer_complete_cb, done_cb=None,
               download_dir=None, ioloop=None):
    self.stateobj = stateobj
    self.transfer_complete_cb = transfer_complete_cb
    self.done_cb = done_cb
    self.download_dir = download_dir
    self.ioloop = ioloop
    self.do_start_called = False
    self.immediate_complete_called = False
    self.faultcode = None
    self.faultstring = None
    self.reboot_callback_called = False
    mock_downloads.append(self)

  def do_start(self):
    self.do_start_called = True

  def do_immediate_complete(self, faultcode, faultstring):
    self.immediate_complete_called = True
    self.faultcode = faultcode
    self.faultstring = faultstring

  def reboot_callback(self, faultcode, faultstring):
    self.reboot_callback_called = True

  def get_queue_state(self):
    return 'This_is_not_a_real_queue_state.'


class DownloadManagerTest(unittest.TestCase):
  def setUp(self):
    self.old_DOWNLOADOBJ = download.DOWNLOADOBJ
    download.DOWNLOADOBJ = MockDownloadObj
    self.tmpdir = tempfile.mkdtemp()
    del mock_downloads[:]

  def tearDown(self):
    download.DOWNLOADOBJ = self.old_DOWNLOADOBJ
    shutil.rmtree(self.tmpdir)
    del mock_downloads[:]

  def allocTestDM(self):
    dm = download.DownloadManager()
    dm.SetDirectories(self.tmpdir, self.tmpdir)
    cmpl = MockTransferComplete()
    dm.send_transfer_complete = cmpl.SendTransferComplete
    return (dm, cmpl)

  def testSimpleDownload(self):
    (dm, _) = self.allocTestDM()
    args = {'command_key': 'TestCommandKey',
            'file_type': 'TestFileType',
            'url': 'http://example.com/',
            'username': 'TestUser',
            'password': 'TestPassword',
            'file_size': 99,
            'target_filename': 'TestFilename',
            'delay_seconds': 30}
    (code, start, end) = dm.NewDownload(**args)
    self.assertEqual(code, 1)
    self.assertEqual(start, 0.0)
    self.assertEqual(end, 0.0)
    self.assertEqual(len(mock_downloads), 1)
    dl = mock_downloads[0]
    self.assertEqual(dl.stateobj.command_key, args['command_key'])
    self.assertEqual(dl.stateobj.file_type, args['file_type'])
    self.assertEqual(dl.stateobj.url, args['url'])
    self.assertEqual(dl.stateobj.username, args['username'])
    self.assertEqual(dl.stateobj.password, args['password'])
    self.assertEqual(dl.stateobj.file_size, args['file_size'])
    self.assertEqual(dl.stateobj.target_filename, args['target_filename'])
    self.assertEqual(dl.stateobj.delay_seconds, args['delay_seconds'])

  def testReadonlyConfigDir(self):
    (dm, _) = self.allocTestDM()
    dm.SetDirectories(config_dir='/user/nonexist', download_dir=self.tmpdir)
    args = {'command_key': 'TestCommandKey',
            'file_type': 'TestFileType',
            'url': 'http://example.com/',
            'username': 'TestUser',
            'password': 'TestPassword',
            'file_size': 99,
            'target_filename': 'TestFilename',
            'delay_seconds': 30}
    (code, start, end) = dm.NewDownload(**args)
    self.assertEqual(code, 1)
    self.assertEqual(start, 0.0)
    self.assertEqual(end, 0.0)
    self.assertEqual(len(mock_downloads), 1)
    dl = mock_downloads[0]
    self.assertEqual(dl.stateobj.command_key, args['command_key'])
    self.assertEqual(dl.stateobj.file_type, args['file_type'])
    self.assertEqual(dl.stateobj.url, args['url'])
    self.assertEqual(dl.stateobj.username, args['username'])
    self.assertEqual(dl.stateobj.password, args['password'])
    self.assertEqual(dl.stateobj.file_size, args['file_size'])
    self.assertEqual(dl.stateobj.target_filename, args['target_filename'])
    self.assertEqual(dl.stateobj.delay_seconds, args['delay_seconds'])

  def testMaxDownloads(self):
    (dm, _) = self.allocTestDM()
    maxdl = download.DownloadManager.MAXDOWNLOADS
    for i in range(maxdl):
      args = {'command_key': 'TestCommandKey' + str(i),
              'url': 'http://example.com/'}
      (code, start, end) = dm.NewDownload(**args)
      self.assertEqual(code, 1)
      self.assertEqual(start, 0.0)
      self.assertEqual(end, 0.0)
    self.assertEqual(len(mock_downloads), maxdl)
    self.assertRaises(core.ResourcesExceededError, dm.NewDownload, **args)

  def testBadUrlScheme(self):
    (dm, _) = self.allocTestDM()
    args = {'command_key': 'TestCommandKey',
            'url': 'invalid://bad.url/'}
    self.assertRaises(core.FileTransferProtocolError, dm.NewDownload, **args)

  def testRestoreMultiple(self):
    (dm, _) = self.allocTestDM()
    numdl = 4
    for i in range(numdl):
      args = {'command_key': 'TestCommandKey' + str(i),
              'file_type': 'TestFileType',
              'url': 'http://example.com/',
              'username': 'TestUser',
              'password': 'TestPassword',
              'file_size': 99,
              'target_filename': 'TestFilename',
              'delay_seconds': 30}
      persistobj.PersistentObject(objdir=dm.config_dir,
                                  rootname=download.DNLDROOTNAME,
                                  filename=None, **args)
    dm.RestoreDownloads()
    self.assertEqual(len(mock_downloads), numdl)
    for i in range(numdl):
      dl = mock_downloads[i]
      self.assertFalse(dl.do_start_called)
      self.assertFalse(dl.immediate_complete_called)
      self.assertTrue(dl.reboot_callback_called)

  def testRestoreNoCommandKey(self):
    (dm, _) = self.allocTestDM()
    args = {'delay_seconds': 30}
    persistobj.PersistentObject(objdir=dm.config_dir,
                                rootname=download.DNLDROOTNAME,
                                filename=None, **args)
    dm.RestoreDownloads()
    self.assertEqual(len(mock_downloads), 0)

  def testRestoreReboots(self):
    (dm, _) = self.allocTestDM()
    expected = set()
    numrb = 3
    for i in range(numrb):
      key = u'TestCommandKey' + str(i)
      args = {'command_key': key}
      persistobj.PersistentObject(objdir=dm.config_dir,
                                  rootname=download.BOOTROOTNAME,
                                  filename=None, **args)
      expected.add(('M Reboot', key))
    # Plus an invalid object
    args = {'foo': 'bar'}
    persistobj.PersistentObject(objdir=dm.config_dir,
                                rootname=download.BOOTROOTNAME,
                                filename=None, **args)
    reboots = set(dm.RestoreReboots())
    self.assertEqual(reboots, expected)

  def testGetAllQueuedTransfers(self):
    (dm, _) = self.allocTestDM()
    numdl = 1
    for i in range(numdl):
      args = {'command_key': 'TestCommandKey' + str(i),
              'file_type': 'TestFileType',
              'url': 'http://example.com/',
              'username': 'TestUser',
              'password': 'TestPassword',
              'file_size': 99,
              'target_filename': 'TestFilename',
              'delay_seconds': 30}
      dm.NewDownload(**args)
    transfers = dm.GetAllQueuedTransfers()
    self.assertEqual(len(transfers), numdl)


if __name__ == '__main__':
  unittest.main()
