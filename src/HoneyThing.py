#!/usr/bin/env python
#
# HoneyThing.py
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import os
import shlex
import subprocess
import BaseHTTPServer

from SocketServer import ThreadingMixIn
from src.config.ConfigReader import ConfigReader
from src.logger.HoneythingLogging import HTLogging
from src.HTTPRequestHandler import HTTPRequestHandler


class ThreadedHTTPServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
    pass


class HoneyThing:

    def __init__(self):

        self.ht = HTLogging()
        self.cfg = ConfigReader()


    '''
    Initialize HTTP server according to stated config
    that try to acs as RomPager server
    '''

    def run_HTTP(self):

        print "Running HTTP..."

        http_listen_address = self.cfg.getConfig("http", "address")
        http_port = self.cfg.getConfig("http", "port")

        httpd = ThreadedHTTPServer((http_listen_address, int(http_port)), HTTPRequestHandler)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()


    '''
    Initialize CWMP server according to stated config
    that communicate with ACS server
    '''

    def run_CWMP(self):

        print "Running CWMP..."

        cwmp_listen_address = self.cfg.getConfig("cwmp", "address")
        cwmp_port = self.cfg.getConfig("cwmp", "port")
        acs_url = self.cfg.getConfig("cwmp", "acs_url")
        socket_file = self.cfg.getConfig("cwmp", "socket_file")
        request_path = self.cfg.getConfig("cwmp", "request_path")

        cpe = os.path.dirname(os.path.abspath(__file__)) + \
              '/cwmp/cwmpd --platform=fakecpe --rcmd-port=0 --cpe-listener ' \
              '-l=%s --port=%s --acs-url=%s --unix-path=%s --ping-path=%s &' \
              % (cwmp_listen_address, cwmp_port, acs_url, socket_file, request_path)

        try:
            subprocess.Popen(shlex.split(cpe))
        except subprocess.CalledProcessError as msg:
            self.ht.logger.error(str(msg.output))
        except OSError:
            pass


    '''
    Main function that runs prepared servers
    '''

    def main(self):

        self.ht.logger.info('Starting Honeything...')
        print('Starting Honeything...')

        self.run_CWMP()
        self.run_HTTP()


if __name__ == '__main__':

    ht = HoneyThing()
    ht.main()