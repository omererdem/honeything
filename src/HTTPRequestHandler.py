#!/usr/bin/env python
#
# HTTPRequestHandler.py
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
import cgi
import Cookie
import BaseHTTPServer

from Auth import Auth
from config.ConfigReader import ConfigReader
from logger.HTTPLogging import HTTPLogging
from logger.HoneythingLogging import HTLogging


class HTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    sys_version = 'UPnP/1.0'
    server_version = 'RomPager/4.07'

    ht = HTLogging()
    http_logging = HTTPLogging()

    '''
    Customized get function (checking application session, specific paths)
    that responds HTTP GET requests
    '''

    def do_GET(self):

        path = self.get_path()
        redirects = {'login'     : '/login_security.html',
                     'login_post': '/Forms/login_security_1.html'}

        if self.path == '/':
            self.show_main_page()

        elif self.path == '/rom-0' or self.path == '/ROM-0':
            self.rom_0(self.get_path('/rom-0'))

        elif os.path.isfile(path):
            if not self.get_session() and self.path not in redirects.values():
                self.redirect_to(redirects['login'])
            else:
                self.handle_data(path)

        else:
            self.show_error_page()


    '''
    Customized post function (handling application authentication process etc.)
    that responds HTTP POST requests
    '''

    def do_POST(self):

        ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        length = int(self.headers.getheader('content-length'))

        if ctype == 'multipart/form-data':
            postvars = cgi.parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            postvars = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
        else:
            postvars = {}

        if self.path == '/Forms/login_security_1.html':

            auth = Auth()

            if auth.http_client_auth(postvars):

                credentials = auth.get_credentials()

                self.send_response(303)
                self.send_header('Location', '/rpSys.html')
                self.send_header('Set-Cookie', 'C0=' + credentials['user'] + '; path=/')
                self.send_header('Set-Cookie', 'C1=' + credentials['pass'] + '; path=/')
                self.end_headers()
                self.log_http(303, postvars)
            else:
                self.do_GET()
                self.log_http(200, postvars)
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.log_http(200, postvars)


    '''
    Get request uri and return full path for it
    @reg_file: Specific uri except from HTTP request path
    @return string
    '''

    def get_path(self, req_file=None):

        cfg = ConfigReader()
        www_dir = os.path.dirname(__file__) + '/' + cfg.getConfig("http", "directory")

        if req_file:
            path = www_dir + req_file
        else:
            if self.path.find('?')>-1:
                path = www_dir + self.path.split('?',1)[0]
            else:
                path = www_dir + self.path

        return path


    '''
    Check if session is exists and return state
    @return: boolean
    '''

    def get_session(self):

        auth = Auth()
        credentials = auth.get_credentials()
        cookie = Cookie.SimpleCookie(self.headers.getheader('Cookie'))
        session = False

        if cookie.has_key('C0') and cookie.has_key('C1'):

            if cookie['C0'].value == credentials['user'] and cookie['C1'].value == credentials['pass']:
                session = True

        return session


    '''
    Get requested file from system and return it to client
    according to extension
    @path: Full path for requested uri
    '''

    def handle_data(self, path):

        ext = os.path.splitext(path)[1].lower()

        content_type = {
            '.css' : 'text/css',
            '.gif' : 'image/gif',
            '.htm' : 'text/html',
            '.html': 'text/html',
            '.jpeg': 'image/jpeg',
            '.jpg' : 'image/jpg',
            '.js'  : 'text/javascript',
            '.png' : 'image/png',
            '.text': 'text/plain',
            '.txt' : 'text/plain'
        }

        if ext in content_type:
            self.send_response(200)
            self.send_header('Content-Type', content_type[ext])
            self.end_headers()

            f = None

            try:
                f = open(path)
                self.wfile.write(f.read())
            except IOError, msg:
                HTTPRequestHandler.ht.logger.error('Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1])

            finally:
                f.close()

            self.log_http(200)

        else:
            self.send_error(415)
            self.log_http(415)


    '''
    Simply redirect client to given url
    @url: Url that is wanted to redirect
    '''

    def redirect_to(self, url):

        self.send_response(301)
        self.send_header('Location', url)
        self.end_headers()
        self.log_http(301)


    '''
    Customized 404 page that can give different response
    to implement vulnerability
    '''

    def show_error_page(self):

        path = self.misfortune_cookie()

        if not path:
            path = self.path

        self.send_response(404)
        self.wfile.write('''\

        <html>
        <head>
        <title>Object Not Found</title></head><body>
        <h1>Object Not Found</h1>
        The requested URL '%s' was not found on the RomPager server.
        <p>Return to <A HREF="http://%s%s">last page</A><p>
        </body></html>

        ''' %(path, self.headers.getheader('Host'), self.path))

        self.log_http(404)


    '''
    Check client session, harmful requests and
    show application main page
    '''

    def show_main_page(self):

        cookie = self.misfortune_cookie()

        if self.get_session():
            self.redirect_to('/rpSys.html')
        elif cookie:
            self.show_error_page()
        else:
            self.redirect_to('/login_security.html')


    '''
    Simply check specific cookie name that is poc for
    "Misfortune Cookie Vulnerability (CVE-2014-9222)" and return its value
    (http://mis.fortunecook.ie/too-many-cooks-exploiting-tr069_tal-oppenheim_31c3.pdf)
    @return: string
    '''

    def misfortune_cookie(self):

        cookie = Cookie.SimpleCookie(self.headers.getheader('Cookie'))

        if cookie.has_key('C107373883'):
            return cookie['C107373883'].value


    '''
    Return rom-0 configuration file without any authentication
    "ROM-0 Backup File Disclosure (CVE-2014-4019)"
    (http://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-4019)
    @path: rom-0 configuration file path
    '''

    def rom_0(self, path):

        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.end_headers()

        try:
            with open(path) as fp:
                self.wfile.write(fp.read())
        except IOError, msg:
            HTTPRequestHandler.ht.logger.error('Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1])

        self.log_http(200)


    '''
    Get logging message dictionary and send it to
    HTTP logging function
    @code: HTTP response code
    @postvar: Variables from HTTP post action
    '''

    def log_http(self, code, postvar=None):

        msg = {
               'client'  : self.client_address,
               'request' : self.requestline,
               'headers' : self.headers,
               'response': [code, self.responses[code][0]],
               'post'    : postvar
              }

        HTTPRequestHandler.http_logging.log_message(msg)