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
Definitions of Json-RPC server side classes.
'''

import sys
import socket
import asyncore
import BaseHTTPServer

from base import dumps, loads, \
                 JsonRpcNotification, JsonRpcRequest, JsonRpcResponse
from errors import JsonRpcError, JsonRpcInternalError, \
                   JsonRpcMethodNotFoundError, JsonRpcInvalidParamsError
from http import HTTP_HEADERS

__metaclass__ = type

class JsonRpcIface:
    '''
    A base class for Json-RPC method interfaces.
    '''
    _handled = False

    def __init__(self, server, request, handler):
        self.server = server
        self.request = request
        self._handler = handler

    def __call__(self):
        method = getattr(self, self.request.method, None)
        try:
            if not callable(method):
                data = {'method': self.request.method}
                raise JsonRpcMethodNotFoundError(data=data)

            args, kwargs = [], self.request.params
            if isinstance(self.request.params, (list, tuple)):
                args, kwargs = self.request.params, {}

            try:
                result = method(*args, **kwargs)
            except TypeError:
                data = {
                    'method': self.request.method,
                    'params': self.request.params
                }
                raise JsonRpcInvalidParamsError(data=data)
        except Exception, err:
            self.on_error(err)
        else:
            if result is not None:
                self.on_result(result)

    def on_result(self, result):
        if self._handled:
            return
        self._handler.on_result(self.request, result)
        self._handled = True

    def on_error(self, error):
        if self._handled:
            return
        if not isinstance(error, JsonRpcError):
            data = {'exception': '%s' % error}
            error = JsonRpcInternalError(data=data)
        self._handler.on_error(self.request, error)
        self._handled = True


class JsonRpcRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    '''
    A class of Json-RPC request handlers.
    '''
    def __init__(self, request, address, server):
        self.request = request
        self.client_address = address
        self.server = server

        self.setup()
        self.handle()

    def handle(self):
        '''
        Handles an Json-RPC request.
        '''
        self.close_connection = 1

        self.raw_requestline = self.rfile.readline()
        if not self.raw_requestline:
            return

        if not self.parse_request():
            return

        if self.command != 'POST':
            self.send_error(501, 'Unsupported method (%r)' % self.command)

        data = self.rfile.read(int(self.headers['content-length']))
        request = loads(data, [JsonRpcNotification, JsonRpcRequest],
                        encoding=self.server.encoding)
        method = self.server.interface(self.server, request, self)
        method()

    def finish(self, data):
        try:
            self.send_response(200)
            for key, value in HTTP_HEADERS.iteritems():
                self.send_header(key, value)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            BaseHTTPServer.BaseHTTPRequestHandler.finish(self)
        finally:
            sys.exc_traceback = None    # Help garbage collection

    def on_result(self, request, result):
        response = JsonRpcResponse(request.id, result)
        data = response.dumps(encoding=self.server.encoding)
        self.finish(data)

    def on_error(self, request, error):
        error.id = request.id
        data = dumps(error.marshal(), encoding=self.server.encoding)
        self.finish(data)


class JsonRpcServer(asyncore.dispatcher):
    '''
    A class of Json-RPC servers.
    '''
    def __init__(self, address, interface, encoding=None):
        if (not isinstance(interface, type) or
            not issubclass(interface, JsonRpcIface)):
            raise TypeError('Interface must be subclass of JsonRpcIface')
        self.interface = interface
        self.encoding = encoding or 'utf-8'
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.listen(0)

    def handle_accept(self):
        request, address = self.accept()
        JsonRpcRequestHandler(request, address, self)

    def handle_error(self):
        try:
            raise
        finally:
            self.handle_close()

    def handle_close(self):
        self.close()

