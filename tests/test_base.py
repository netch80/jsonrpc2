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
Provides unit tests for the Json-RPC2 base.py module.
'''

import json
import unittest

from jsonrpc2 import base
from jsonrpc2 import errors

class ErrorsTest(unittest.TestCase):
    def test_default_marshal(self):
        error = errors.JsonRpcError()
        result = {
            'error': {
                'code': -32000,
                'message': 'JSON-RPC error.'
            },
            'id': None
        }
        self.assertEqual(error.marshal(), result)

    def test_custom_marshal(self):
        error = errors.JsonRpcError(10000, 'Test error message',
                                    '_test_id_', {'test': 'data'})
        result = {
            'error': {
                'code': -10000,
                'message': 'Test error message',
                'data': {'test': 'data'}
            },
            'id': '_test_id_'
        }
        self.assertEqual(error.marshal(), result)


class MessagesTest(unittest.TestCase):
    def test_dumps_notification(self):
        params = {
            'a': 1,
            'b': 'test'
        }
        notification = base.JsonRpcNotification('foo', params)
        result = {
            'jsonrpc': base.VERSION,
            'method': 'foo',
            'params': params
        }
        self.assertEqual(json.loads(notification.dumps()), result)

    def test_dumps_request(self):
        params = {
            'a': 1,
            'b': 'test'
        }
        request = base.JsonRpcRequest('foo', params, '_test_id_')
        result = {
            'jsonrpc': base.VERSION,
            'method': 'foo',
            'params': params,
            'id': '_test_id_'
        }
        self.assertEqual(json.loads(request.dumps()), result)

    def test_dumps_request_gen_id(self):
        params = {
            'a': 1,
            'b': 'test'
        }
        request = base.JsonRpcRequest('foo', params)
        self.assertTrue(isinstance(request.id, basestring)
                        and len(request.id) == 8)
        result = {
            'jsonrpc': base.VERSION,
            'method': 'foo',
            'params': params,
            'id': request.id
        }
        self.assertEqual(json.loads(request.dumps()), result)

    def test_dumps_response(self):
        params = {
            'a': 1,
            'b': 'test'
        }
        response = base.JsonRpcResponse('_test_id_', params)
        result = {
            'jsonrpc': base.VERSION,
            'result': params,
            'id': '_test_id_'
        }
        self.assertEqual(json.loads(response.dumps()), result)

