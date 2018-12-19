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
Provides the echo example client.
'''

import logging

from jsonrpc2 import loop, JsonRpcClient

def run():
    def _on_result(result):
        message = result['echo']
        logging.info('Echo: %s' % message)
        return message

    def on_result(result):
        message = _on_result(result)
        message += '.1'
        logging.info('Say: %s' % message)
        client.say([message], _on_result, on_error)

    def on_error(error):
        logging.error('Echo error: %s [%s]' % (error, error.data))

    client = JsonRpcClient('http://localhost:8081', timeout=5)
    for i in range(1, 6):
        message = 'Hello -> %d' % i
        logging.info('Say: %s' % message)
        client.say([message], on_result, on_error)
    loop()

