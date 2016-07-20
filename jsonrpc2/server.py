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

import logger
from base import dumps, loads, VERSION, \
                 JsonRpcNotification, JsonRpcRequest, JsonRpcResponse
from errors import JsonRpcError, JsonRpcInternalError, \
                   JsonRpcMethodNotFoundError, JsonRpcInvalidParamsError
from http import HTTP_HEADERS

__metaclass__ = type

class JsonRpcIface:
    '''
    A base class for Json-RPC method interfaces.
    '''
    def __init__(self, server, request, handler):
        self.server = server
        self.request = request
        self._handler = handler

    def __call__(self):
        '''
        Calls an interface method from the current request.
        '''
        method = getattr(self, self.request.method, None)
        logger.debug('Call request: method=%s, params=%s'
                      % (method, self.request.params))
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
        '''
        A callback method that dispatches the given result of a requested
        method to a client.
        '''
        logger.debug('Call request: result=%s' % result)
        self._handler.on_result(self.request, result)
        self._handled = True

    def on_error(self, error):
        '''
        A callback method that dispatches the given error of a requested
        method to a client.
        '''
        logger.debug('Call request: error=%s' % error)
        self._handler.on_error(self.request, error)
        self._handled = True


class JsonRpcRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    '''
    A class of Json-RPC request handlers.
    '''
    # The server software version
    server_version = 'JsonRPC2/%s' % VERSION

    # The supported version of the HTTP protocol
    protocol_version = 'HTTP/1.1'

    # The default request version
    default_request_version = 'HTTP/1.1'

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
        self.command = None
        self.requestline = ''
        self.request_version = self.default_request_version
        self.close_connection = 1

        try:
            self.raw_requestline = self.rfile.readline()
            if not self.raw_requestline:
                return

            if not self.parse_request():
                return

            if self.command != 'POST':
                self.send_error(501, 'Unsupported method (%r)' % self.command)
                return

            data = self.rfile.read(int(self.headers.get('content-length', 0)))
        except socket.timeout:
            self.send_error(408, 'Request timed out')
            return

        request = None
        try:
            request = loads(data, [JsonRpcNotification, JsonRpcRequest],
                            encoding=self.server.encoding)
            method = self.server.interface(self.server, request, self)
            method()
        except Exception, err:
            self.on_error(request, err)
        finally:
            if isinstance(request, JsonRpcNotification):
                self.close()

    def finish(self, data):
        '''
        Finishes handling an Json-RPC request by sending a response to
        the corresponding client.
        '''
        try:
            self.send_response(200)
            for key, value in HTTP_HEADERS.iteritems():
                self.send_header(key, value)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            self.close()
        except socket.error:
            logger.exception('Send response error')
        finally:
            sys.exc_traceback = None    # Help garbage collection

    def close(self):
        '''
        Closes a connection to the corresponding client.
        '''
        BaseHTTPServer.BaseHTTPRequestHandler.finish(self)

    def log_message(self, format, *args):
        logger.debug(format % args)

    def on_result(self, request, result):
        if isinstance(request, JsonRpcNotification):
            return
        response = JsonRpcResponse(request.id, result)
        data = response.dumps(encoding=self.server.encoding)
        self.finish(data)

    def on_error(self, request, error):
        if isinstance(request, JsonRpcNotification):
            return
        if not isinstance(error, JsonRpcError):
            data = {'exception': '%s' % error}
            error = JsonRpcInternalError(data=data)
        if request:
            error.id = request.id
        data = dumps(error.marshal(), encoding=self.server.encoding)
        self.finish(data)


class JsonRpcServer(asyncore.dispatcher):
    '''
    A class of Json-RPC servers.
    '''
    #: A class of Json-RPC request handlers
    handler_class = JsonRpcRequestHandler

    def __init__(self, address, interface, timeout=None,
                       encoding=None, logging=None, allowed_ips=None):
        if (not isinstance(interface, type) or
            not issubclass(interface, JsonRpcIface)):
            raise TypeError('Interface must be JsonRpcIface subclass')

        self.allowed_ips = allowed_ips
        self.interface = interface
        self.timeout = timeout
        self.encoding = encoding or 'utf-8'
        logger.setup(logging)

        try:
            asyncore.dispatcher.__init__(self)
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            self.bind(address)
            self.listen(0)
        except Exception:
            logger.exception('Server run error')
            raise

    def __repr__(self):
        addr = '%s:%d' % self.addr
        return '<%s(%s) at %#x>' % (self.__class__.__name__, addr, id(self))

    __str__ = __repr__

    def handle_accept(self):
        '''
        Runs a handler for a new Json-RPC request.
        '''
        accept_result = self.accept()
        if accept_result is not None:
            request, address = accept_result
            if self.allowed_ips is None or address[0] in self.allowed_ips:
                logger.debug('Handle client: %s:%d' % address)
                request.settimeout(self.timeout)
                self.handler_class(request, address, self)
            else:
                logger.debug('Rejecting connection from: %s:%d' % address)
                request.close()

    def handle_error(self):
        logger.exception('Unhandled server error')

    def handle_close(self):
        '''
        Closes the Json-RPC server.
        '''
        logger.info('Handle close server')
        self.close()
