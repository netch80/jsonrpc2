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
Provides the complex example client.
'''

import random
import logging

from jsonrpc2 import loop, JsonRpcClient

def on_result(result):
    logging.info('Server result: %s' % result)

def on_error(error):
    logging.error('Server error: %s [%s]' % (error, error.data))

def run():
    client = JsonRpcClient('http://localhost:8082')

    for i in xrange(-1, 5):
        x = random.choice(xrange(1, 6))
        logging.info('Power: %s ^ %s' % (x, i))
        client.power([x, i], on_result, on_error)
    loop()

