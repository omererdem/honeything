#!/usr/bin/env python
#
# Auth.py
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


import hashlib

from config.ConfigReader import ConfigReader


class Auth:

    def __init__(self):
        cfg = ConfigReader()

        self.username = cfg.getConfig('authentication', 'http_user')
        self.password = cfg.getConfig('authentication', 'http_pass')


    '''
    Check user credentials and return
    whether authentication is success or not
    @postvars : User credentials from post action
    @return: boolean
    '''

    def http_client_auth(self, postvars):

        if postvars['Login_Name'][0] == self.username and \
                        postvars['uiWebLoginhiddenPassword'][0] == self.password:
            return True
        else:
            return False


    '''
    Get user credentials from configuration file
    and return md5sum of them
    @return: dictionary
    '''

    def get_credentials(self):

        credentials = {'user': hashlib.md5(self.username).hexdigest(),
                       'pass': self.password}

        return credentials