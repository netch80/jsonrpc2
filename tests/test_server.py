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
Provides unit tests for the Json-RPC2 server.py module.
'''

import json
import random
import socket
import httplib
import urllib2
import unittest

from jsonrpc2 import base
from jsonrpc2 import server
from jsonrpc2 import errors

class TestIface(server.JsonRpcIface):
    def test_result(self, a, b=2):
        return {'status': 'OK',
                'params': {'a': a, 'b': b}}

    def test_on_result(self, a, b):
        self.on_result({'status': 'OK',
                        'params': {'a': a, 'b': b}})

    def test_exception(self, a):
        raise Exception(str(a))

    def test_on_error(self, a):
        self.on_error(Exception(str(a)))


class TestHandler(server.JsonRpcRequestHandler):
    def __init__(self, *args, **kwargs):
        server.JsonRpcRequestHandler.__init__(self, *args, **kwargs)

    def send_error(self, code, message=None):
        self.server.resp_code = code
        server.JsonRpcRequestHandler.send_error(self, code, message)
        self.server.close()
        self.request.close()

    def send_response(self, code, message=None):
        self.server.resp_code = code
        server.JsonRpcRequestHandler.send_response(self, code, message)
        self.server.close()
        self.request.close()


class ServerTestBase(unittest.TestCase):
    def setUp(self):
        self.port = random.randint(10000, 65000)
        self.server = server.JsonRpcServer(('localhost', self.port),
                                           TestIface, timeout=0.2)
        self.server.handler_class = TestHandler
        self.server.resp_code = None

    def tearDown(self):
        self.server.close()


class ServerBasicTest(ServerTestBase):
    def test_invalid_interface(self):
        try:
            server.JsonRpcServer(('localhost', self.port + 1),
                                 base.JsonRpcBase)
        except TypeError, err:
            self.assertEqual(str(err), 'Interface must be JsonRpcIface subclass')
        else:
            self.assertFalse(True)

    def test_tcp_empty(self):
        client = socket.create_connection(('localhost', self.port), 1)
        base.loop()
        client.close()
        self.assertEqual(self.server.resp_code, 408)

    def test_tcp_data(self):
        client = socket.create_connection(('localhost', self.port), 1)
        client.send('Test tcp data\n')
        base.loop()
        client.close()
        self.assertEqual(self.server.resp_code, 400)

    def test_http_get(self):
        client = socket.create_connection(('localhost', self.port), 1)
        client.send('GET / HTTP/1.1\r\n\r\n')
        base.loop()
        client.close()
        self.assertEqual(self.server.resp_code, 501)

    def test_http_post_empty(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = 'POST / HTTP/1.1\r\nContent-Length: 0\r\n\r\n'
        client.send(data)
        base.loop()
        resp = httplib.HTTPResponse(client)
        resp.begin()
        data = resp.read()
        client.close()
        self.assertEqual(self.server.resp_code, 200)
        try:
            base.loads(data)
        except errors.JsonRpcError, err:
            self.assertEqual(err.code, -32700)
            self.assertEqual(err.message, 'Parse error.')

    def test_http_post_broken_data(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = 'POST / HTTP/1.1\r\nContent-Length: 1024\r\n\r\nTest broken data'
        client.send(data)
        base.loop()
        client.close()
        self.assertEqual(self.server.resp_code, 408)

    def test_http_post_data(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = 'POST / HTTP/1.1\r\nContent-Length: 14\r\n\r\nTest text data'
        client.send(data)
        base.loop()
        resp = httplib.HTTPResponse(client)
        resp.begin()
        data = resp.read()
        client.close()
        self.assertEqual(self.server.resp_code, 200)
        try:
            base.loads(data)
        except errors.JsonRpcError, err:
            self.assertEqual(err.code, -32700)
            self.assertEqual(err.message, 'Parse error.')


class ServerJsonRpcTest(ServerTestBase):
    def test_notification(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = '''POST / HTTP/1.1\r
Content-Length: 67\r
\r
{"jsonrpc": "2.0", "method": "test_result", "params": [123, "abc"]}'''
        client.send(data)
        base.loop(count=1)
        resp = httplib.HTTPResponse(client)
        self.assertRaises(httplib.BadStatusLine, resp.begin)
        self.assertEqual(self.server.resp_code, None)
        client.close()

    def test_call_method_list_params(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = '''POST / HTTP/1.1\r
Content-Length: 85\r
\r
{"jsonrpc": "2.0", "id": "12345abc", "method": "test_result", "params": [123, "abc"]}'''
        client.send(data)
        base.loop()
        resp = httplib.HTTPResponse(client)
        resp.begin()
        data = resp.read()
        client.close()
        self.assertEqual(self.server.resp_code, 200)
        response = base.loads(data, [base.JsonRpcResponse])
        self.assertTrue(isinstance(response, base.JsonRpcResponse))
        self.assertEqual(response.id, '12345abc')
        self.assertEqual(response.result, {'status': 'OK',
                                           'params': {'a': 123, 'b': 'abc'}})

    def test_call_method_dict_params(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = '''POST / HTTP/1.1\r
Content-Length: 85\r
\r
{"jsonrpc": "2.0", "id": "12345abc", "method": "test_result", "params": {"a": "abc"}}'''
        client.send(data)
        base.loop()
        resp = httplib.HTTPResponse(client)
        resp.begin()
        data = resp.read()
        client.close()
        self.assertEqual(self.server.resp_code, 200)
        response = base.loads(data, [base.JsonRpcResponse])
        self.assertTrue(isinstance(response, base.JsonRpcResponse))
        self.assertEqual(response.id, '12345abc')
        self.assertEqual(response.result, {'status': 'OK',
                                           'params': {'a': 'abc', 'b': 2}})

    def test_call_method_not_found(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = '''POST / HTTP/1.1\r
Content-Length: 102\r
\r
{"jsonrpc": "2.0", "id": "12345abc", "method": "method_not_found", "params": {"a": "abc", "b": "efg"}}'''
        client.send(data)
        base.loop()
        resp = httplib.HTTPResponse(client)
        resp.begin()
        data = resp.read()
        client.close()
        self.assertEqual(self.server.resp_code, 200)
        try:
            base.loads(data, [base.JsonRpcResponse])
        except errors.JsonRpcError, err:
            self.assertEqual(err.code, -32601)
            self.assertEqual(err.message, 'Method not found.')
            self.assertEqual(err.data, {'method': 'method_not_found'})

    def test_call_invalid_list_params(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = '''POST / HTTP/1.1\r
Content-Length: 91\r
\r
{"jsonrpc": "2.0", "id": "12345abc", "method": "test_result", "params": [123, "abc", true]}'''
        client.send(data)
        base.loop()
        resp = httplib.HTTPResponse(client)
        resp.begin()
        data = resp.read()
        client.close()
        self.assertEqual(self.server.resp_code, 200)
        try:
            base.loads(data, [base.JsonRpcResponse])
        except errors.JsonRpcError, err:
            self.assertEqual(err.code, -32602)
            self.assertEqual(err.message, 'Invalid params.')
            self.assertEqual(err.data, {'method': 'test_result',
                                        'params': [123, 'abc', True]})

    def test_call_invalid_dict_params(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = '''POST / HTTP/1.1\r
Content-Length: 106\r
\r
{"jsonrpc": "2.0", "id": "12345abc", "method": "test_result", "params": {"a": 123, "b": "abc", "c": true}}'''
        client.send(data)
        base.loop()
        resp = httplib.HTTPResponse(client)
        resp.begin()
        data = resp.read()
        client.close()
        self.assertEqual(self.server.resp_code, 200)
        try:
            base.loads(data, [base.JsonRpcResponse])
        except errors.JsonRpcError, err:
            self.assertEqual(err.code, -32602)
            self.assertEqual(err.message, 'Invalid params.')
            self.assertEqual(err.data, {'method': 'test_result',
                                        'params': {'a': 123, 'b': 'abc', 'c': True}})

    def test_interface_on_result(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = '''POST / HTTP/1.1\r
Content-Length: 88\r
\r
{"jsonrpc": "2.0", "id": "12345abc", "method": "test_on_result", "params": [123, "abc"]}'''
        client.send(data)
        base.loop()
        resp = httplib.HTTPResponse(client)
        resp.begin()
        data = resp.read()
        client.close()
        self.assertEqual(self.server.resp_code, 200)
        response = base.loads(data, [base.JsonRpcResponse])
        self.assertTrue(isinstance(response, base.JsonRpcResponse))
        self.assertEqual(response.id, '12345abc')
        self.assertEqual(response.result, {'status': 'OK',
                                           'params': {'a': 123, 'b': 'abc'}})

    def test_interface_exception(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = '''POST / HTTP/1.1\r
Content-Length: 83\r
\r
{"jsonrpc": "2.0", "id": "12345abc", "method": "test_exception", "params": ["abc"]}'''
        client.send(data)
        base.loop()
        resp = httplib.HTTPResponse(client)
        resp.begin()
        data = resp.read()
        client.close()
        self.assertEqual(self.server.resp_code, 200)
        try:
            base.loads(data, [base.JsonRpcResponse])
        except errors.JsonRpcError, err:
            self.assertEqual(err.code, -32603)
            self.assertEqual(err.message, 'Internal error.')
            self.assertEqual(err.data, {'exception': 'abc'})

    def test_interface_on_error(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = '''POST / HTTP/1.1\r
Content-Length: 82\r
\r
{"jsonrpc": "2.0", "id": "12345abc", "method": "test_on_error", "params": ["efg"]}'''
        client.send(data)
        base.loop()
        resp = httplib.HTTPResponse(client)
        resp.begin()
        data = resp.read()
        client.close()
        self.assertEqual(self.server.resp_code, 200)
        try:
            base.loads(data, [base.JsonRpcResponse])
        except errors.JsonRpcError, err:
            self.assertEqual(err.code, -32603)
            self.assertEqual(err.message, 'Internal error.')
            self.assertEqual(err.data, {'exception': 'efg'})

    def test_call_method_few_times(self):
        client = socket.create_connection(('localhost', self.port), 1)
        data = '''POST / HTTP/1.1\r
Content-Length: 85\r
\r
{"jsonrpc": "2.0", "id": "12345abc", "method": "test_result", "params": [123, "abc"]}'''
        client.send(data)
        client.send(data)
        client.send(data)
        base.loop()
        # First
        resp = httplib.HTTPResponse(client)
        resp.begin()
        data = resp.read()
        self.assertEqual(self.server.resp_code, 200)
        response = base.loads(data, [base.JsonRpcResponse])
        self.assertTrue(isinstance(response, base.JsonRpcResponse))
        self.assertEqual(response.id, '12345abc')
        self.assertEqual(response.result, {'status': 'OK',
                                           'params': {'a': 123, 'b': 'abc'}})
        # Second...
        resp = httplib.HTTPResponse(client)
        try:
            resp.begin()
        except httplib.BadStatusLine, err:
            self.assertEqual(str(err), "''")
        else:
            self.assertFalse(True)
        finally:
            client.close()
