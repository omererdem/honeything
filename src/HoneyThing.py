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


import BaseHTTPServer

from HTTPRequestHandler import HTTPRequestHandler
from config.ConfigReader import ConfigReader
from logger.HoneythingLogging import HTLogging


class HoneyThing:

    def __init__(self):

        self.ht = HTLogging()

    '''
    Initialize HTTP server according to stated config
    that try to acs as RomPager server
    '''

    def main(self):

        self.ht.logger.info('Starting Honeything...')
        print('Starting Honeything...')

        cfg = ConfigReader()
        server_address = cfg.getConfig("http", "address")
        server_port = cfg.getConfig("http", "port")
        httpd = BaseHTTPServer.HTTPServer((server_address, int(server_port)), HTTPRequestHandler)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        httpd.server_close()


if __name__ == '__main__':

    ht = HoneyThing()
    ht.main()