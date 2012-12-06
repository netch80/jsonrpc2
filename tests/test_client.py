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
Provides unit tests for the Json-RPC2 client.py module.
'''

import json
import random
import socket
import httplib
import urllib2
import asyncore
import unittest

from jsonrpc2 import base
from jsonrpc2 import client
from jsonrpc2 import errors

HTTP_REQ_LINE = 'POST / HTTP/1.1\r\n'

class TestServer(asyncore.dispatcher):
    _callback = None

    def __init__(self, host='localhost', port=8080, timeout=1):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind((host, port))
        self.listen(0)

    def connect_callback(self, callback):
        self._callback = callback

    def handle_accept(self):
        sock, address = self.accept()
        data = sock.recv(100*1024)
        if self._callback:
            data = self._callback(data)
            if data:
                sock.send(data)
        self.close()


class ClientTestBase(unittest.TestCase):
    def setUp(self):
        self._request = None
        self._result = None
        self.port = random.randint(10000, 65000)
        self.client = client.JsonRpcClient('http://localhost:%d' % self.port)
        self.server = TestServer(port=self.port)
        self.server.connect_callback(self._request_callback)

    def tearDown(self):
        self.server.close()

    def _request_callback(self, data):
        try:
            self.assertTrue(data.startswith(HTTP_REQ_LINE))
            self._request = base.loads(data.split('\r\n\r\n')[1],
                                       [base.JsonRpcRequest])
        except Exception, err:
            self._request = err

    def _assert_message(self, msg, msg_type=base.JsonRpcRequest):
        if isinstance(msg, AssertionError):
            raise msg
        self.assertTrue(isinstance(msg, msg_type))


class ClientBasicTest(ClientTestBase):
    def test_empty_tcp_response(self):
        def callback(data):
            self._request_callback(data)
            return ''

        def on_error(error):
            self._result = error

        self.server.connect_callback(callback)
        self.client.foo(on_error=on_error)
        base.loop()
        self._assert_message(self._request, base.JsonRpcRequest)
        self._assert_message(self._result, errors.JsonRpcResponseError)
        self.assertEqual(self._result.id, self._request.id)
        self.assertEqual(self._result.code, -32650)
        self.assertEqual(self._result.message, 'Invalid response.')
        self.assertEqual(self._result.data, {'exception': ''})

    def test_tcp_response_data(self):
        def callback(data):
            self._request_callback(data)
            return 'Test tcp data'

        def on_error(error):
            self._result = error

        self.server.connect_callback(callback)
        self.client.foo(on_error=on_error)
        base.loop()
        self._assert_message(self._request, base.JsonRpcRequest)
        self._assert_message(self._result, errors.JsonRpcResponseError)
        self.assertEqual(self._result.id, self._request.id)
        self.assertEqual(self._result.code, -32650)
        self.assertEqual(self._result.message, 'Invalid response.')
        self.assertEqual(self._result.data, {'exception': 'Test tcp data'})

    def test_http_get_response(self):
        def callback(data):
            self._request_callback(data)
            return 'GET / HTTP/1.1\r\n\r\n'

        def on_error(error):
            self._result = error

        self.server.connect_callback(callback)
        self.client.foo(on_error=on_error)
        base.loop()
        self._assert_message(self._request, base.JsonRpcRequest)
        self._assert_message(self._result, errors.JsonRpcResponseError)
        self.assertEqual(self._result.id, self._request.id)
        self.assertEqual(self._result.code, -32650)
        self.assertEqual(self._result.message, 'Invalid response.')
        self.assertEqual(self._result.data, {'exception': 'GET / HTTP/1.1\r\n'})

    def test_response_timeout(self):
        def on_error(error):
            self._result = error

        self.client.timeout = 0.1
        self.server.del_channel()

        context = self.client.foo(on_error=on_error)
        self.assertTrue(isinstance(context, client.JsonRpcContext))
        base.loop()
        self._assert_message(context.request, base.JsonRpcRequest)
        self._assert_message(self._result, errors.JsonRpcProtocolError)
        self.assertEqual(self._result.id, context.request.id)
        self.assertEqual(self._result.code, 110)

    def test_connection_refused(self):
        def on_error(error):
            self._result = error

        self.client.url = 'http://localhost:%d' % (self.port + 1)
        context = self.client.foo(on_error=on_error)
        self.assertTrue(isinstance(context, client.JsonRpcContext))
        #base.loop()
        self._assert_message(context.request, base.JsonRpcRequest)
        self._assert_message(self._result, errors.JsonRpcProtocolError)
        self.assertEqual(self._result.id, context.request.id)
        self.assertEqual(self._result.code, 111)


class ClientRequestTest(ClientTestBase):

    _response_format = '''HTTP/1.1 200 OK\r
Content-Type: application/json-rpc\r
Content-Length: %d\r
\r
%s'''

    def _format_response(self, msg):
        data = msg.dumps() if hasattr(msg, 'dumps') else base.dumps(msg)
        return self._response_format % (len(data), data)

    def test_request_method(self):
        context = self.client.foo()
        self.assertTrue(isinstance(context, client.JsonRpcContext))
        self.assertFalse(context.closed())
        base.loop()
        self._assert_message(self._request, base.JsonRpcRequest)
        self.assertEqual(self._request.id, context.request.id)
        self.assertEqual(self._request.method, 'foo')
        self.assertEqual(self._request.params, None)

    def test_request_method_list_params(self):
        params = ['abc', 123, {'a': 1, 'b': 2, 'c': 3}]
        self.client.foo_list(params)
        base.loop()
        self._assert_message(self._request, base.JsonRpcRequest)
        self.assertEqual(self._request.method, 'foo_list')
        self.assertEqual(self._request.params, params)

    def test_request_method_dict_params(self):
        params = {'a': 1, 'b': 'def', 'c': [3, 6, 9]}
        self.client.foo_dict(params)
        base.loop()
        self._assert_message(self._request, base.JsonRpcRequest)
        self.assertEqual(self._request.method, 'foo_dict')
        self.assertEqual(self._request.params, params)

    def test_request_method_result(self):
        def callback(data):
            self._request_callback(data)
            msg = base.JsonRpcResponse(self._request.id, result)
            return self._format_response(msg)

        def on_result(result):
            self._result = result

        result = {'status': 'OK'}
        self.server.connect_callback(callback)
        self.client.foo(on_result=on_result)
        base.loop()
        self._assert_message(self._request, base.JsonRpcRequest)
        self.assertEqual(self._result, result)

    def test_request_method_error(self):
        def callback(data):
            self._request_callback(data)
            msg = errors.JsonRpcError(id=self._request.id, **error)
            return self._format_response(msg.marshal())

        def on_error(error):
            self._result = error

        error = {
            'code': -12345,
            'message': 'Test error message',
            'data': {'exception': 'Test exception'}
        }
        self.server.connect_callback(callback)
        self.client.foo(on_error=on_error)
        base.loop()
        self._assert_message(self._request, base.JsonRpcRequest)
        self._assert_message(self._result, errors.JsonRpcError)
        self.assertEqual(self._result.id, self._request.id)
        self.assertEqual(self._result.marshal()['error'], error)

    def test_request_method_invalid_response_id(self):
        def callback(data):
            self._request_callback(data)
            msg = base.JsonRpcResponse('a1b2c3d4', None)
            return self._format_response(msg)

        def on_error(error):
            self._result = error

        self.server.connect_callback(callback)
        self.client.foo(on_error=on_error)
        base.loop()
        self._assert_message(self._request, base.JsonRpcRequest)
        self._assert_message(self._result, errors.JsonRpcResponseError)
        self.assertEqual(self._result.id, self._request.id)
        self.assertEqual(self._result.code, -32650)
        self.assertEqual(self._result.message, 'Invalid response.')
        self.assertEqual(self._result.data, {'id': 'a1b2c3d4'})

    def test_request_method_http_error(self):
        def callback(data):
            self._request_callback(data)
            return '''HTTP/1.1 501 Unsupported method ('GET')\r
Content-Type: application/json-rpc\r
Content-Length: 15\r
\r
<html />'''

        def on_error(error):
            self._result = error

        self.server.connect_callback(callback)
        self.client.foo(on_error=on_error)
        base.loop()
        self._assert_message(self._request, base.JsonRpcRequest)
        self._assert_message(self._result, errors.JsonRpcProtocolError)
        self.assertEqual(self._result.id, self._request.id)
        self.assertEqual(self._result.code, 501)
        self.assertEqual(self._result.message, "Unsupported method ('GET')")
        self.assertEqual(self._result.data, {'exception': '<html />'})


class ClientNotificationTest(ClientTestBase):
    def _request_callback(self, data):
        try:
            self.assertTrue(data.startswith(HTTP_REQ_LINE))
            self._request = base.loads(data.split('\r\n\r\n')[1],
                                       [base.JsonRpcNotification])
        except Exception, err:
            self._request = err

    def test_notify_method(self):
        context = self.client.foo.notify()
        self.assertTrue(isinstance(context, client.JsonRpcContext))
        self.assertTrue(context.closed())
        base.loop()
        self._assert_message(self._request, base.JsonRpcNotification)
        self.assertEqual(self._request.method, 'foo')
        self.assertEqual(self._request.params, None)

    def test_notify_method_notifier(self):
        self.client.notifier = True
        context = self.client.foo()
        self.assertTrue(isinstance(context, client.JsonRpcContext))
        self.assertTrue(context.closed())
        base.loop()
        self._assert_message(self._request, base.JsonRpcNotification)
        self.assertEqual(self._request.method, 'foo')
        self.assertEqual(self._request.params, None)

    def test_notify_method_list_params(self):
        params = ['abc', 123, {'a': 1, 'b': 2, 'c': 3}]
        self.client.foo_list.notify(params)
        base.loop()
        self._assert_message(self._request, base.JsonRpcNotification)
        self.assertEqual(self._request.method, 'foo_list')
        self.assertEqual(self._request.params, params)

    def test_notify_method_dict_params(self):
        params = {'a': 1, 'b': 'def', 'c': [3, 6, 9]}
        self.client.foo_dict.notify(params)
        base.loop()
        self._assert_message(self._request, base.JsonRpcNotification)
        self.assertEqual(self._request.method, 'foo_dict')
        self.assertEqual(self._request.params, params)

