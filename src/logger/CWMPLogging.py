#!/usr/bin/env python
#
# CWMPLogging.py
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


from BaseLogging import BaseLogging
from src.config.ConfigReader import ConfigReader


class CWMPLogging(BaseLogging):

    def __init__(self):

        format = "%(asctime)s \t%(message)s"
        BaseLogging.__init__(self, 'cwmp', 'file_cwmp', format)

        self.cfg = ConfigReader()


    '''
    Get CWMP log message and write it to
    file in readable/parseable format.
    @message: CWMP communication info (IPs, headers, data etc.)
    '''

    def log_message(self, message):

        fmt = self.cfg.getConfig('logging', 'cwmp_data_format')

        if fmt == 'hex':
            message['data'] = message['data'].encode('hex')

        if not message['method']:
            message['method'] = '-'

        msg = [
            message['source_ip'],                                  # Source IP
            str(message['source_port']),                           # Source Port
            message['destination_ip'],                             # Destination IP
            str(message['destination_port']),                      # Destination Port
            message['type'],                                       # Type (POST, RECEIVE)
            message['method'],                                     # CWMP Method Name
            str(message['headers']),                               # Headers
            '\n' + message['data']                                 # CWMP Method Data
        ]

        for val in msg:
            if not val:
                message[val] = '-'

        log = ''

        for value in msg:
            log += value + '\t'

        self.logger.critical(log)