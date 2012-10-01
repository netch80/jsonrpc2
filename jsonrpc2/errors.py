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
Definitions of Json-RPC exception classes.
'''

class JsonRpcError(Exception):
    '''
    A base class of Json-RPC errors.

    {
        "jsonrpc": "2.0",
        "id": "1",
        "error": {
            "code": -32000,
            "message": "JSON-RPC error.",
            "data": {}
        }
    }
    '''
    def __init__(self, code=32000, message='JSON-RPC error.',
                       id=None, data=None):
        if code > 0:
            code = -code
        Exception.__init__(self, (code, message))
        self.id = id
        self.code = code
        self.message = message
        self.data = data

    def marshal(self):
        error = {
            'code': self.code,
            'message': self.message
        }
        if self.data:
            error['data'] = self.data
        return {
            'error': error,
            'id': self.id
        }


# Standard errors:

class JsonRpcParseError(JsonRpcError):
    def __init__(self, data=None):
        JsonRpcError.__init__(self, 32700, 'Parse error.', data=data)

class InvalidJsonRpcError(JsonRpcError):
    def __init__(self, data=None):
        JsonRpcError.__init__(self, 32600, 'Invalid JSON-RPC.', data=data)

class JsonRpcMethodNotFoundError(JsonRpcError):
    def __init__(self, id=None, data=None):
        JsonRpcError.__init__(self, 32601, 'Method not found.', id, data=data)

class JsonRpcInvalidParamsError(JsonRpcError):
    def __init__(self, id=None, data=None):
        JsonRpcError.__init__(self, 32602, 'Invalid params.', id, data=data)

class JsonRpcInternalError(JsonRpcError):
    def __init__(self, id=None, data=None):
        JsonRpcError.__init__(self, 32603, 'Internal error.', id, data=data)

