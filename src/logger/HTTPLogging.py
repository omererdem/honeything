#!/usr/bin/env python
#
# HTTPLogging.py
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


class HTTPLogging(BaseLogging):

    def __init__(self):

        format = "%(asctime)s \t%(message)s"
        BaseLogging.__init__(self, 'http', 'file_http', format)

        self.cfg = ConfigReader()
        self.log_extended = self.cfg.getConfig('logging', 'http_extended')


    '''
    Get HTTP log message and write it to
    file in readable/parseable format.
    @message: HTTP logging values (headers, IPs, etc.)
    '''

    def log_message(self, message):

        request =  message['request'].split()
        headers = ['Host', 'Referer', 'User-Agent', 'Cookie']

        for val in headers:
            if val not in message['headers']:
                message['headers'][val] = '-'

        if not message['post']:
            message['post'] = '-'

        msg = [
            str(message['client'][0]),                                  # Source IP
            str(message['client'][1]),                                  # Source Port
            str(message['headers']['Host']),                            # Destination IP
            str(self.cfg.getConfig('http', 'port')),                    # Destination Port
            str(request[0]),                                            # Method
            str(request[1]),                                            # Uri
            str(message['response'][1]),                                # Status Message
        ]

        if self.log_extended == "yes":

            msg.insert(5, str(message['headers']['Host']))              # Host
            msg.insert(7, str(message['headers']['Referer']))           # Referer
            msg.insert(8, str(message['headers']['User-Agent']))        # User-Agent
            msg.insert(9, str(message['response'][0]))                  # Status Code
            msg.extend([str(message['headers']['Cookie']),              # Cookie
                        str(message['post'])])                          # POST Method Variables

        log = ''

        for value in msg:
            log += value + '\t'

        self.logger.critical(log)