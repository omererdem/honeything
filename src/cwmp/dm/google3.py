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

"""Fix sys.path so it can find our libraries.

This file is named google3.py because gpylint specifically ignores it when
complaining about the order of import statements - google3 should always
come before other non-python-standard imports.
"""

__author__ = 'apenwarr@google.com (Avery Pennarun)'


import os.path
import sys

mydir = os.path.dirname(__file__)
sys.path += [
    os.path.join(mydir, '..'),
]
import tr.google3  #pylint: disable-msg=C6204,W0611
