#!/usr/bin/env python
# This file is part of Json-RPC2.
#
# Copyright (C) 2012 Marcin Lyko
# All rights reserved.
#
# Json-RPC2 is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# Json-RPC2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Json-RPC2; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
Provides the echo example server.
'''

import logging

from jsonrpc2 import loop, JsonRpcIface, JsonRpcServer

class EchoIface(JsonRpcIface):
    def say(self, message):
        logging.info('Echo: %s' % message)
        return {'echo': message}


def run():
    server = JsonRpcServer(('localhost', 8081), EchoIface)
    loop()

