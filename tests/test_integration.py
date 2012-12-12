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
Provides unit tests for the Json-RPC2 client-server integration.
'''

import random
import unittest

from jsonrpc2 import base
from jsonrpc2 import client
from jsonrpc2 import server
from jsonrpc2 import errors

class TestIface(server.JsonRpcIface):
    def test_result(self, a, b=2):
        self.server.request = self.request
        return {'status': 'OK',
                'params': {'a': a, 'b': b}}

    def test_exception(self, a):
        self.server.request = self.request
        raise Exception(str(a))

class TestHandler(server.JsonRpcRequestHandler):
    def close(self):
        server.JsonRpcRequestHandler.close(self)
        self.server.close()


class IntegrationTest(unittest.TestCase):
    def setUp(self):
        self.port = random.randint(10000, 65000)
        self.client = client.JsonRpcClient('http://localhost:%d' % self.port,
                                           timeout=0.2)
        self.server = server.JsonRpcServer(('localhost', self.port),
                                           TestIface, timeout=0.2)
        self.server.handler_class = TestHandler
        self.server.request = None
        self._result = None
        self._error = None

    def tearDown(self):
        self.server.close()

    def _on_result(self, result):
        self._result = result

    def _on_error(self, error):
        self._error = error

    def test_notify_method_list_params(self):
        params = ['abc', {'a': 1, 'b': 2, 'c': 3}]
        self.client.notifier = True
        self.client.test_result(params)
        base.loop()
        self.assertTrue(isinstance(self.server.request, base.JsonRpcNotification))
        self.assertEqual(self.server.request.method, 'test_result')
        self.assertEqual(self.server.request.params, params)
        self.assertEqual(self._result, None)
        self.assertEqual(self._error, None)

    def test_notify_method_dict_params(self):
        params = {'b': 'def', 'a': [3, 6, 9]}
        self.client.notifier = True
        self.client.test_result(params)
        base.loop()
        self.assertTrue(isinstance(self.server.request, base.JsonRpcNotification))
        self.assertEqual(self.server.request.method, 'test_result')
        self.assertEqual(self.server.request.params, params)
        self.assertEqual(self._result, None)
        self.assertEqual(self._error, None)

    def test_notify_method_error(self):
        params = [1]
        self.client.notifier = True
        self.client.test_exception(params)
        base.loop()
        self.assertTrue(isinstance(self.server.request, base.JsonRpcNotification))
        self.assertEqual(self.server.request.method, 'test_exception')
        self.assertEqual(self.server.request.params, params)
        self.assertEqual(self._result, None)
        self.assertEqual(self._error, None)

    def test_request_method_list_params(self):
        params = ['abc', {'a': 1, 'b': 2, 'c': 3}]
        self.client.test_result(params, on_result=self._on_result,
                                on_error=self._on_error)
        base.loop()
        self.assertTrue(isinstance(self.server.request, base.JsonRpcRequest))
        self.assertEqual(self.server.request.method, 'test_result')
        self.assertEqual(self.server.request.params, params)
        self.assertEqual(self._result, {'status': 'OK',
                                        'params': {'a': params[0],
                                                   'b': params[1]}})
        self.assertEqual(self._error, None)

    def test_request_method_dict_params(self):
        params = {'b': 'def', 'a': [3, 6, 9]}
        self.client.test_result(params, on_result=self._on_result,
                                on_error=self._on_error)
        base.loop()
        self.assertTrue(isinstance(self.server.request, base.JsonRpcRequest))
        self.assertEqual(self.server.request.method, 'test_result')
        self.assertEqual(self.server.request.params, params)
        self.assertEqual(self._result, {'status': 'OK',
                                        'params': params})
        self.assertEqual(self._error, None)

    def test_request_method_error(self):
        params = [1]
        self.client.test_exception(params, on_result=self._on_result,
                                   on_error=self._on_error)
        base.loop()
        self.assertTrue(isinstance(self.server.request, base.JsonRpcRequest))
        self.assertEqual(self.server.request.method, 'test_exception')
        self.assertEqual(self.server.request.params, params)
        self.assertTrue(isinstance(self._error, errors.JsonRpcError))
        self.assertEqual(self.server.request.id, self._error.id)
        self.assertEqual(self._error.marshal()['error'], {'code': -32603,
                                                 'message': 'Internal error.',
                                                 'data': {'exception': '1'}})
        self.assertEqual(self._result, None)

