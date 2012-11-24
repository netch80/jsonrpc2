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
Definitions of Json-RPC client side classes.
'''

import json
import urllib2

import logger
from http import HttpRequestContext
from base import loads, JsonRpcRequest, JsonRpcResponse
from errors import JsonRpcError, JsonRpcProtocolError, JsonRpcResponseError

__metaclass__ = type

class JsonRpcProcessor(urllib2.BaseHandler):
    '''
    A class of Json-RPC response processors.
    '''
    handler_order = 9999

    def __init__(self, context):
        self.context = context

    def http_response(self, request, response):
        '''
        Processes the given Json-RPC response.
        '''
        if response.code == 200:
            message = loads(response.read(), [JsonRpcResponse],
                            encoding=self.context.client.encoding)
            if request.id != message.id:
                raise JsonRpcResponseError(data={'id': message.id})
            return message.result
        raise JsonRpcProtocolError(response.code, response.msg,
                                   data={'exception': response.read()})

    https_response = http_response


class JsonRpcContext(HttpRequestContext):
    '''
    A class of Json-RPC request contexts.
    '''
    def __init__(self, client, request):
        self.client = client
        self.request = request
        data = request.dumps(encoding=self.client.encoding)
        HttpRequestContext.__init__(self, self.client.url, data,
                                    JsonRpcProcessor(self))

    def call(self, on_result, on_error):
        self._run(on_result, on_error, timeout=self.client.timeout)

    def notify(self):
        self._run(timeout=self.client.timeout)
        self._response.close()

    def on_error(self, error):
        if isinstance(error, urllib2.URLError):
            code = 400
            message = str(error.reason)
            try:
                code, message = error.reason[:2]
            except ValueError:
                pass
            error = JsonRpcProtocolError(code, message)
        if not isinstance(error, JsonRpcError):
            error = JsonRpcResponseError(data={'exception': str(error)})
        error.id = self.request.id
        HttpRequestContext.on_error(self, error)


class JsonRpcMethod:
    '''
    A class of Json-RPC method calls.
    '''
    def __init__(self, method, client):
        self.method = method
        self.client = client

    def __call__(self, params=None, on_result=None, on_error=None):
        request = JsonRpcRequest(self.method, params)
        return self.client.request(request, on_result, on_error)


class JsonRpcClient:
    '''
    A class of Json-RPC clients.
    '''
    #: Default HTTP path
    _http_path = '/RPC2'

    def __init__(self, url, timeout=None, encoding=None, logging=None):
        self.url = url
        self.timeout = timeout
        self.encoding = encoding or 'utf-8'
        logger.setup(logging)

    def __getattr__(self, method):
        return JsonRpcMethod(method, self)

    def request(self, request, on_result=None, on_error=None):
        logger.debug('Call request: url=%r, method=%r, parmas=%r'
                      % (self.url, request.method, request.params))
        context = JsonRpcContext(self, request)
        context.call(on_result, on_error)
        return context

