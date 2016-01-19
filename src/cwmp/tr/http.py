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
#pylint: disable-msg=W0404
#
"""Implement the TR-069 style request/response protocol over HTTP."""

__author__ = 'apenwarr@google.com (Avery Pennarun)'

import binascii
import collections
import datetime
import os
import random
import socket
import sys
import time
import urllib

from curtain import digest
import tornado.httpclient
import tornado.ioloop
import tornado.util
import tornado.web

import api_soap
import cpe_management_server
import cwmp_session
import helpers

import soap
from urlparse import urlparse
from src.logger.CWMPLogging import CWMPLogging
from src.logger.HoneythingLogging import HTLogging

PROC_IF_INET6 = '/proc/net/if_inet6'
MAX_EVENT_QUEUE_SIZE = 64
cwmp = CWMPLogging()
ht = HTLogging()

def _Shorten(s, prefixofs, suffixofs, maxlen):
  """Shorten the given string if its length is >= maxlen.

  Note: maxlen should generally be considerably bigger than
  prefixofs + suffixofs.  It's disconcerting to a reader when
  you have a "..." to replace 10 bytes, but it feels fine when the
  "..." replaces 500 bytes.

  Args:
    s: the string to shorten.
    prefixofs: the number of chars to keep at the beginning of s.
    suffixofs: the number of chars to keep at the end of s.
    maxlen: if the string is longer than this, shorten it.
  Returns:
    A shortened version of the string.
  """
  s = str(s)
  if len(s) >= maxlen and not os.environ.get('DONT_SHORTEN'):
    # When the string exceeds the limit, we deliberately shorten it to
    # considerably less than the limit, because it's disconcerting when
    # you have a "..." to replace 10 bytes, but it feels right when the
    # "..." replaces 500 bytes.
    s = s[0:prefixofs] + '\n........\n' + s[-suffixofs:]
  return s


class LimitDeque(collections.deque):
  """Wrapper around a deque that limits the maximimum size.

  If the maximum size is reached, call the supplied handler, or
  exit if no handler is provided.
  """

  def __init__(self, max_size=None, handler=None):
    collections.deque.__init__(self)
    self.max_size = max_size
    self.handler = handler

  def CheckSize(self):
    if self.max_size and len(self) > self.max_size:
      if self.handler:
        self.handler()
      else:
        #print 'Maximum length of deque (%d) was exceeded' % (self.max_size)
        ht.logger.error('Maximum length of deque (%d) was exceeded' % (self.max_size))
        sys.exit(1)

  def append(self, *args):
    collections.deque.append(self, *args)
    self.CheckSize()

  def appendleft(self, *args):
    collections.deque.appendleft(self, *args)
    self.CheckSize()

  def extend(self, *args):
    collections.deque.extend(self, *args)
    self.CheckSize()

  def extendleft(self, *args):
    collections.deque.extendleft(self, *args)
    self.CheckSize()


# SPEC3 = TR-069_Amendment-3.pdf
# http://www.broadband-forum.org/technical/download/TR-069_Amendment-3.pdf
def SplitUrl(url):
  Url = collections.namedtuple('Url', ('method host port path'))
  method, rest = urllib.splittype(url)
  hostport, path = urllib.splithost(rest)
  host, port = urllib.splitport(hostport)
  return Url(method, host, int(port or 0), path)


class PingHandler(digest.DigestAuthMixin, tornado.web.RequestHandler):
  """Handles accesses to the ConnectionRequestURL.

  Args:
    callback: the function to call when theURL is accessed.
    cpe_ms: the cpe_management_server object, from which to retrieve
      username and password.
  """

  def initialize(self, callback, cpe_ms):
    self.callback = callback
    self.cpe_ms = cpe_ms

  def getcredentials(self, username):
    credentials = {'auth_username': self.cpe_ms.ConnectionRequestUsername,
                   'auth_password': self.cpe_ms.ConnectionRequestPassword}
    if username == credentials['auth_username']:
      return credentials

  def get(self):
    # Digest authentication handler
    if self.get_authenticated_user(self.getcredentials, 'Authusers'):
      return self.set_status(self.callback())


class Handler(tornado.web.RequestHandler):
  def initialize(self, soap_handler):
    self.soap_handler = soap_handler

  def get(self):
    self.write('This is the cpe/acs handler.  It only takes POST requests.')

  def post(self):
    #print 'TR-069 server: request received:\n%s' % self.request.body
    ht.logger.info('TR-069 server: request received')
    if self.request.body.strip():
      result = self.soap_handler(self.request.body)
      self.write(str(result))


class CPEStateMachine(object):
  """A tr-69 Customer Premises Equipment implementation.

  Args:
    ip: local ip address to bind to. If None, find address automatically.
    cpe: the api_soap.cpe object for this device
    listenport: the port number to listen on for ACS ping requests.
    acs_url: An ACS URL to use. This overrides platform_config.GetAcsUrl()
    ping_path: URL path for the ACS Ping function
    ping_ip6dev: ifname to use for the CPE Ping address.
    fetch_args: kwargs to pass to HTTPClient.fetch
  """



  def __init__(self, ip, cpe, listenport, platform_config, ping_path,
               acs_url=None, ping_ip6dev=None, fetch_args=dict(), ioloop=None,
               restrict_acs_hosts=None):
    self.cpe = cpe
    self.cpe_soap = api_soap.CPE(self.cpe)
    self.encode = api_soap.Encode()
    self.outstanding = None
    self.response_queue = []
    self.request_queue = []
    self.event_queue = LimitDeque(MAX_EVENT_QUEUE_SIZE, self.EventQueueHandler)
    self.ioloop = ioloop or tornado.ioloop.IOLoop.instance()
    self.retry_count = 0  # for Inform.RetryCount
    self.start_session_timeout = None  # timer for CWMPRetryInterval
    self.session = None
    self.my_configured_ip = ip
    self.ping_ip6dev = ping_ip6dev
    self.fetch_args = fetch_args
    self.rate_limit_seconds = 60
    self.platform_config = platform_config
    self.previous_ping_time = 0
    self.ping_timeout_pending = None
    self._changed_parameters = set()
    self._changed_parameters_sent = set()
    self.cpe_management_server = cpe_management_server.CpeManagementServer(
        acs_url=acs_url, platform_config=platform_config, port=listenport,
        ping_path=ping_path, get_parameter_key=cpe.getParameterKey,
        start_periodic_session=self.NewPeriodicSession, ioloop=self.ioloop,
        restrict_acs_hosts=restrict_acs_hosts)


  def EventQueueHandler(self):
    """Called if the event queue goes beyond the maximum threshold."""
    #print 'Event queue has grown beyond the maximum size, restarting...'
    #print 'event_queue=%s' % (str(self.event_queue))
    ht.logger.error('Event queue has grown beyond the maximum size, restarting...')
    ht.logger.error('event_queue=%s' % (str(self.event_queue)))
    sys.exit(1)

  def GetManagementServer(self):
    """Return the ManagementServer implementation for tr-98/181."""
    return self.cpe_management_server

  def Send(self, req):
    self.request_queue.append(str(req))
    self.Run()

  def SendResponse(self, req):
    self.response_queue.append(str(req))
    self.Run()

  def LookupDevIP6(self, name):
    """Returns the global IPv6 address for the named interface."""
    with open(PROC_IF_INET6, 'r') as f:
      for line in f:
        fields = line.split()
        if len(fields) < 6:
          continue
        scope = int(fields[3].strip())
        dev = fields[5].strip()
        if dev == name and scope == 0:
          bin_ip = binascii.unhexlify(fields[0])
          return socket.inet_ntop(socket.AF_INET6, bin_ip)
    return 0

  def _GetLocalAddr(self):
    if self.my_configured_ip is not None:
      return self.my_configured_ip
    if self.ping_ip6dev is not None:
      return self.LookupDevIP6(self.ping_ip6dev)
    acs_url = self.cpe_management_server.URL
    if not acs_url:
      return 0

    # If not configured with an address it gets a bit tricky: we try connecting
    # to the ACS, non-blocking, so we can find out which local IP the kernel
    # uses when connecting to that IP.  The local address is returned with
    # getsockname(). Then we can tell the ACS to use that address for
    # connecting to us later.  We use a nonblocking socket because we don't
    # care about actually connecting; we just care what the local kernel does
    # in its implicit bind() when we *start* connecting.
    url = SplitUrl(acs_url)
    host = url.host
    port = url.port or 0
    s = socket.socket()
    s.setblocking(0)
    try:
      s.connect((host, port or 1))  # port doesn't matter, but can't be 0
    except socket.error:
      pass
    return s.getsockname()

  def EncodeInform(self):
    """Return an Inform message for this session."""
    if not self.session.my_ip:
      local_ip_port = self._GetLocalAddr()
      self.session.my_ip = local_ip_port[0]
      self.session.my_port = local_ip_port[1]
      self.cpe_management_server.my_ip = local_ip_port[0]
    events = []
    for ev in self.event_queue:
      events.append(ev)
    parameter_list = []
    try:
      ms = self.cpe.root.GetExport('InternetGatewayDevice.ManagementServer')
      di = self.cpe.root.GetExport('InternetGatewayDevice.DeviceInfo')
      parameter_list += [
          ('InternetGatewayDevice.ManagementServer.ConnectionRequestURL',
           ms.ConnectionRequestURL),
          ('InternetGatewayDevice.ManagementServer.ParameterKey',
           ms.ParameterKey),
          ('InternetGatewayDevice.DeviceInfo.HardwareVersion',
           di.HardwareVersion),
          ('InternetGatewayDevice.DeviceInfo.SoftwareVersion',
           di.SoftwareVersion),
          ('InternetGatewayDevice.DeviceInfo.SpecVersion', di.SpecVersion),
      ]
      # NOTE(jnewlin): Changed parameters can be set to be sent either
      # explicitly with a value change event, or to be sent with the
      # periodic inform.  So it's not a bug if there is no value change
      # event in the event queue.

      # Take all of the parameters and put union them with the another
      # set that has been previously sent.  When we receive an inform
      # from the ACS we clear the _sent version.  This fixes a bug where
      # we send this list of params to the ACS, followed by a PerioidStat
      # adding itself to the list here, followed by getting an ack from the
      # ACS where we clear the list.  Now we just clear the list of the
      # params that was sent when the ACS acks.
      self._changed_parameters_sent.update(self._changed_parameters)
      self._changed_parameters.clear()
      parameter_list += self._changed_parameters_sent
    except (AttributeError, KeyError):
      pass
    req = self.encode.Inform(root=self.cpe.root, events=events,
                             retry_count=self.retry_count,
                             parameter_list=parameter_list)
    return str(req)

  def SendTransferComplete(self, command_key, faultcode, faultstring,
                           starttime, endtime, event_code):
    if not self.session:
      tc = ('7 TRANSFER COMPLETE', None)
      if tc not in self.event_queue:
        self.event_queue.appendleft(tc)
      self.event_queue.append((event_code, command_key))
    cmpl = self.encode.TransferComplete(command_key, faultcode, faultstring,
                                        starttime, endtime)
    self.Send(cmpl)

  def GetNext(self):
    if not self.session:
      return None
    if self.session.inform_required():
      self.session.state_update(sent_inform=True)
      return self.EncodeInform()
    if self.response_queue and self.session.response_allowed():
      return self.response_queue.pop(0)
    if self.request_queue and self.session.request_allowed():
      return self.request_queue.pop(0)
    return ''

  def Run(self):
    #print 'RUN'
    if not self.session:
      #print 'No ACS session, returning.'
      ht.logger.info('No ACS session, returning.')
      return
    if not self.session.acs_url:
      #print 'No ACS URL populated, returning.'
      ht.logger.info('No ACS URL populated, returning.')
      self._ScheduleRetrySession(wait=60)
      return
    if self.session.should_close():
      #print 'Idle CWMP session, terminating.'
      ht.logger.info('Idle CWMP session, terminating.')
      self.outstanding = None
      ping_received = self.session.close()
      self.platform_config.AcsAccessSuccess(self.session.acs_url)
      self.session = None
      self.retry_count = 0  # Successful close
      if self._changed_parameters:
        # Some values triggered during the prior session, start a new session
        # with those changed params.  This should also satisfy a ping.
        self.NewValueChangeSession()
      elif ping_received:
        # Ping received during session, start another
        self._NewPingSession()
      return

    if self.outstanding is not None:
      # already an outstanding request
      return
    if self.outstanding is None:
      self.outstanding = self.GetNext()
    if self.outstanding is None:
      # We're not allowed to send anything yet, session not fully open.
      return

    headers = {}
    if self.session.cookies:
      headers['Cookie'] = ';'.join(self.session.cookies)
    if self.outstanding:
      headers['Content-Type'] = 'text/xml; charset="utf-8"'
      headers['SOAPAction'] = ''
    else:
      # Empty message
      self.session.state_update(cpe_to_acs_empty=True)
    self.platform_config.AcsAccessAttempt(self.session.acs_url)

    # Log CPE Post Message

    msg = {
            'source_ip'       : self.session.my_ip,
            'source_port'     : self.session.my_port,
            'destination_ip'  : urlparse(self.session.acs_url).hostname,
            'destination_port': urlparse(self.session.acs_url).port,
            'type'            : 'CPE_POST',
            'method'          : self.GetCWMPMethodName(self.outstanding),
            'headers'         : headers,
            'data'            : self.outstanding
          }

    cwmp.log_message(msg)

    #print('CPE POST (at {0!s}):\n'
    #      'ACS URL: {1!r}\n'
    #      '{2!s}\n'
    #      '{3!s}'.format(time.ctime(), self.session.acs_url,
    #                     headers, _Shorten(self.outstanding, 768, 256, 2048)))
    req = tornado.httpclient.HTTPRequest(
        url=self.session.acs_url, method='POST', headers=headers,
        body=self.outstanding, follow_redirects=True, max_redirects=5,
        request_timeout=30.0, use_gzip=True, allow_ipv6=True,
        **self.fetch_args)
    self.session.http.fetch(req, self.GotResponse)

  def GotResponse(self, response):
    self.outstanding = None
    #print 'CPE RECEIVED (at %s):' % time.ctime()
    if not self.session:
      #print 'Session terminated, ignoring ACS message.'
      ht.logger.info('Session terminated, ignoring ACS message.')
      return
    if not response.error:
      cookies = response.headers.get_list('Set-Cookie')
      if cookies:
        self.session.cookies = cookies
      #print _Shorten(response.body, 768, 256, 2048)

      msg = {
                'source_ip'        : urlparse(self.session.acs_url).hostname,
                'source_port'      : urlparse(self.session.acs_url).port,
                'destination_ip'   : self.session.my_ip,
                'destination_port' : self.session.my_port,
                'type'             : 'CPE_RECEIVED',
                'method'           : self.GetCWMPMethodName(response.body),
                'headers'          : response.headers,
                'data'             : response.body
      }

      cwmp.log_message(msg)

      if response.body:
        out = self.cpe_soap.Handle(response.body)
        if out is not None:
          self.SendResponse(out)
        # TODO(dgentry): $SPEC3 3.7.1.6 ACS Fault 8005 == retry same request
      else:
        self.session.state_update(acs_to_cpe_empty=True)
    else:
      #print 'HTTP ERROR {0!s}: {1}'.format(response.code, response.error)
      ht.logger.error('HTTP ERROR {0!s}: {1}'.format(response.code, response.error))
      self._ScheduleRetrySession()
    self.Run()
    return 200

  def _ScheduleRetrySession(self, wait=None):
    """Start a timer to retry a CWMP session.

    Args:
      wait: Number of seconds to wait. If wait=None, choose a random wait
        time according to $SPEC3 section 3.2.1
    """
    if self.session:
      self.session.close()
      self.session = None
    if wait is None:
      self.retry_count += 1
      wait = self.cpe_management_server.SessionRetryWait(self.retry_count)
    self.start_session_timeout = self.ioloop.add_timeout(
        datetime.timedelta(seconds=wait), self._SessionWaitTimer)

  def _SessionWaitTimer(self):
    """Handler for the CWMP Retry timer, to start a new session."""
    self.start_session_timeout = None
    self.session = cwmp_session.CwmpSession(
        acs_url=self.cpe_management_server.URL, ioloop=self.ioloop)
    self.Run()

  def _CancelSessionRetries(self):
    """Cancel any pending CWMP session retry."""
    if self.start_session_timeout:
      self.ioloop.remove_timeout(self.start_session_timeout)
      self.start_session_timeout = None
    self.retry_count = 0

  def _NewSession(self, reason):
    if not self.session:
      self._CancelSessionRetries()
      self.event_queue.appendleft((reason, None))
      self.session = cwmp_session.CwmpSession(
          acs_url=self.cpe_management_server.URL, ioloop=self.ioloop)
      self.Run()

  def _NewTimeoutPingSession(self):
    if self.ping_timeout_pending:
      self.ping_timeout_pending = None
      self._NewPingSession()

  def _NewPingSession(self):
    if self.session:
      # $SPEC3 3.2.2 initiate at most one new session after this one closes.
      self.session.ping_received = True
      return

    # Rate limit how often new sessions can be started with ping to
    # once a minute
    current_time = helpers.monotime()
    elapsed_time = current_time - self.previous_ping_time
    allow_ping = (elapsed_time < 0 or
                  elapsed_time > self.rate_limit_seconds)
    if allow_ping:
      self.ping_timeout_pending = None
      self.previous_ping_time = current_time
      self._NewSession('6 CONNECTION REQUEST')
    elif not self.ping_timeout_pending:
      # Queue up a new session via tornado.
      callback_time = self.rate_limit_seconds - elapsed_time
      if callback_time < 1:
        callback_time = 1
      self.ping_timeout_pending = self.ioloop.add_timeout(
          datetime.timedelta(seconds=callback_time),
          self._NewTimeoutPingSession)

  def NewPeriodicSession(self):
    # If the ACS stops responding for some period of time, it's possible
    # that we'll already have a periodic inform queued up.
    # In this case, don't start the new inform, wait for the session
    # retry.  The retry has a maximum timer of periodic session.
    reason = '2 PERIODIC'
    if not (reason, None) in self.event_queue:
      self._NewSession(reason)

  def SetNotificationParameters(self, parameters):
    """Set the list of parameters that have changed.

    The list of parameters that have triggered and should be sent either
    with the next periodic inform, or the next active active value change
    session.

    Args:
      parameters: An array of the parameters that have changed, these
      need to be sent to the ACS in the parameter list.
    """
    for param in parameters:
      self._changed_parameters.add(param)

  def NewValueChangeSession(self):
    """Start a new session to the ACS for the parameters that have changed."""

    # If all the changed parameters have been reported, or there is already
    # a session running, don't do anything.  The run loop for the session
    # will autmatically kick off a new session if there are new changed
    # parameters.
    if not self._changed_parameters or self.session:
      return

    reason = '4 VALUE CHANGE'
    if not (reason, None) in self.event_queue:
      self._NewSession(reason)

  def PingReceived(self):
    self._NewPingSession()
    return 204  # No Content

  def _RemoveFromDequeue(self, dq, rmset):
    """Return a new deque which removes events in rmset."""
    newdq = collections.deque()
    for event in dq:
      (reason, unused_command_key) = event
      if reason.lower() not in rmset:
        newdq.append(event)
    return newdq

  def TransferCompleteReceived(self):
    """Called when the ACS sends a TransferCompleteResponse."""
    reasons = frozenset(['7 transfer complete', 'm download',
                         'm scheduledownload', 'm upload'])
    self.event_queue = self._RemoveFromDequeue(self.event_queue, reasons)

  def InformResponseReceived(self):
    """Called when the ACS sends an InformResponse."""
    reasons = frozenset(['0 bootstrap', '1 boot', '2 periodic',
                         '3 scheduled', '4 value change',
                         '6 connection request', '8 diagnostics complete',
                         'm reboot', 'm scheduleinform'])
    self.event_queue = self._RemoveFromDequeue(self.event_queue, reasons)
    self._changed_parameters_sent.clear()

  def Startup(self):
    rb = self.cpe.download_manager.RestoreReboots()
    if rb:
      self.event_queue.extend(rb)
    # TODO(dgentry) Check whether we have a config, send '1 BOOT' instead
    self._NewSession('0 BOOTSTRAP')
    # This will call SendTransferComplete, so we have to already be in
    # a session.
    self.cpe.startup()

  def GetCWMPMethodName(self, message):
    message = str(message)
    if message:
      return soap.Parse(message).Body[0].name


def Listen(ip, port, ping_path, acs, cpe, cpe_listener, platform_config,
           acs_url=None, ping_ip6dev=None, fetch_args=dict(), ioloop=None,
           restrict_acs_hosts=None):
  if not ping_path:
    ping_path = '/ping/%x' % random.getrandbits(120)
  while ping_path.startswith('/'):
    ping_path = ping_path[1:]
  cpe_machine = CPEStateMachine(ip=ip, cpe=cpe, listenport=port,
                                platform_config=platform_config,
                                ping_path=ping_path,
                                restrict_acs_hosts=restrict_acs_hosts,
                                acs_url=acs_url, ping_ip6dev=ping_ip6dev,
                                fetch_args=fetch_args, ioloop=ioloop)
  cpe.setCallbacks(cpe_machine.SendTransferComplete,
                   cpe_machine.TransferCompleteReceived,
                   cpe_machine.InformResponseReceived)
  handlers = []
  if acs:
    acshandler = api_soap.ACS(acs).Handle
    handlers.append(('/acs', Handler, dict(soap_handler=acshandler)))
    #print 'TR-069 ACS at http://*:%d/acs' % port
    ht.logger.info('TR-069 ACS at http://*:%d/acs' % port)
  if cpe and cpe_listener:
    cpehandler = cpe_machine.cpe_soap.Handle
    handlers.append(('/cpe', Handler, dict(soap_handler=cpehandler)))
    #print 'TR-069 CPE at http://*:%d/cpe' % port
    ht.logger.info('TR-069 CPE at http://*:%d/cpe' % port)
  if ping_path:
    handlers.append(('/' + ping_path, PingHandler,
                     dict(cpe_ms=cpe_machine.cpe_management_server,
                          callback=cpe_machine.PingReceived)))
    #print 'TR-069 callback at http://*:%d/%s' % (port, ping_path)
    ht.logger.info('TR-069 callback at http://*:%d/%s' % (port, ping_path))
  webapp = tornado.web.Application(handlers)
  webapp.listen(port)
  return cpe_machine
