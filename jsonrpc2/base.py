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
Basic functions and defintions of Json-RPC message classes.
'''

import json
import random
import string
import asyncore
import logger

from errors import JsonRpcError, JsonRpcParseError, InvalidJsonRpcError

# The version number
VERSION = '0.2.2'

# Json-RPC specification version
SPEC_VER = '2.0'

_ID_CHARSET = string.ascii_letters + string.digits

__metaclass__ = type

def _gen_id(length=8):
    '''
    Generates random message ID.
    '''
    return ''.join([random.choice(_ID_CHARSET) for i in xrange(length)])

def dumps(message, encoding=None):
    '''
    Serializes the Json-RPC message given as dictionary object to a JSON
    formatted data using the specified encoding.

    Raises a JsonRpcParseError exception if the message cannot be serialized.
    '''
    logger.debug('Dumps message: %s' % message)
    if not encoding:
        encoding = 'utf-8'
    message['jsonrpc'] = SPEC_VER
    try:
        return json.dumps(message, encoding=encoding)
    except TypeError, err:
        data = {'exception': '%s' % err}
        raise JsonRpcParseError(data=data)

def loads(data, classes=[], encoding=None):
    '''
    Deserializes the given JSON formatted data to a Json-RPC message of one of
    the specified classes using the specified encoding.

    Raises a JsonRpcError exception if the message cannot be deserialized to
    a message of one the specified classes.
    '''
    logger.debug('Loads message: %s' % data)
    if not encoding:
        encoding = 'utf-8'
    try:
        message = json.loads(data, encoding=encoding)
    except ValueError, err:
        data = {'exception': '%s' % err}
        raise JsonRpcParseError(data=data)
    # Basic JSON-RPC validation
    if (not isinstance(message, dict) or
        message.pop('jsonrpc', None) != SPEC_VER):
        raise InvalidJsonRpcError()
    # JSON-RPC message validation
    for cls in classes:
        try:
            return cls(**message)
        except TypeError:
            pass
    try:
        raise JsonRpcError(id=message['id'], **message['error'])
    except (TypeError, KeyError), err:
        data = {'exception': '%s' % err}
        raise JsonRpcParseError(data=data)


def loop(timeout=1, count=None):
    '''
    Runs an asynchronous event loop.
    '''
    asyncore.loop(timeout=timeout, use_poll=True, count=count)


class JsonRpcBase:
    '''
    A base class for Json-RPC messages.
    '''
    def dumps(self, message, encoding=None):
        return dumps(message, encoding=encoding)

class JsonRpcNotification(JsonRpcBase):
    '''
    A class of Json-RPC notifications:
    {
        "jsonrpc": "2.0",
        "method": "foo",
        "params": null
    }
    '''
    def __init__(self, method, params):
        self.method = method
        self.params = params

    def dumps(self, encoding=None):
        notification = {
            'method': self.method,
            'params': self.params
        }
        return JsonRpcBase.dumps(self, notification, encoding=encoding)

class JsonRpcRequest(JsonRpcBase):
    '''
    A class of Json-RPC requests:
    {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "foo",
        "params": null
    }
    '''
    def __init__(self, method, params, id=None):
        self.id = id or _gen_id()
        self.method = method
        self.params = params

    def dumps(self, encoding=None):
        request = {
            'method': self.method,
            'params': self.params,
            'id': self.id
        }
        return JsonRpcBase.dumps(self, request, encoding=encoding)

class JsonRpcResponse(JsonRpcBase):
    '''
    A class of Json-RPC responses:
    {
        "jsonrpc": "2.0",
        "id": "1",
        "result": null
    }
    '''
    def __init__(self, id, result):
        self.id = id
        self.result = result

    def dumps(self, encoding=None):
        response = {
            'result': self.result,
            'id': self.id
        }
        return JsonRpcBase.dumps(self, response, encoding=encoding)

