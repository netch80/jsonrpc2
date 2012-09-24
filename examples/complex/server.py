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

from jsonrpc2 import loop, JsonRpcClient, JsonRpcIface, JsonRpcServer

class MultiplyIface(JsonRpcIface):
    def multiply(self, x, y):
        logging.info('Multiply: %s * %s' % (x, y))
        return {
            'x': x,
            'y': y,
            'result': x * y
        }


class ComplexIface(JsonRpcIface):
    client = None
    i = 1
    n = 0
    x = 1

    def _on_multiply_result(self, result):
        result = result['result']
        if self.i < self.n:
            self.i += 1
            self.client.multiply([result, self.x],
                                 self._on_multiply_result, self.on_error)
        else:
            self.on_result({'x': self.x, 'n': self.n, 'result': result})

    def power(self, x, n):
        logging.info('Power: %s ^ %s' % (x, n))
        self.i = 2
        self.n = n
        self.x = x
        if n < 0:
            x = 1.0 / x
            n = -n
        if n == 0:
            return {
                'x': self.x,
                'n': self.n,
                'result': 1
            }
        elif n == 1:
            return {
                'x': self.x,
                'n': self.n,
                'result': x
            }
        self.i = 2
        self.client = JsonRpcClient('http://localhost:8092')
        self.client.multiply([x, x], self._on_multiply_result, self.on_error)


def run():
    multiply_server = JsonRpcServer(('localhost', 8092), MultiplyIface)
    complex_server = JsonRpcServer(('localhost', 8082), ComplexIface)
    loop()

