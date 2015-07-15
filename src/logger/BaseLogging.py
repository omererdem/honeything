#!/usr/bin/env python
#
# BaseLogging.py
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


import logging

from src.config.ConfigReader import ConfigReader


class BaseLogging:

    def __init__(self, name, file, format):

        cfg = ConfigReader()

        logfile = cfg.getConfig('logging', file)
        loglevel = cfg.getConfig('logging', 'level')

        self.name = name
        formatter = logging.Formatter(format)
        self.log_handler = logging.FileHandler(logfile)
        self.log_handler.setFormatter(formatter)
        self.initialize_logger(loglevel)


    '''
    Set log level and create new logger instance
    @level: String that identifies level type
    '''

    def initialize_logger(self, level):

        logger = logging.getLogger(self.name)

        if level == "DEBUG":
            logger.setLevel(logging.DEBUG)
        elif level == "WARNING":
            logger.setLevel(logging.WARNING)
        elif level == "CRITICAL":
            logger.setLevel(logging.CRITICAL)
        elif level == "ERROR":
            logger.setLevel(logging.ERROR)
        else:
            logger.setLevel(logging.INFO)

        if not logger.handlers:
            logger.addHandler(self.log_handler)

        self.logger = logger