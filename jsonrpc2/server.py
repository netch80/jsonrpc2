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

import time
import email
import socket
import asyncore

from . import logger
from .base import dumps, loads, VERSION, \
                 JsonRpcNotification, JsonRpcRequest, JsonRpcResponse
from .errors import JsonRpcError, JsonRpcInternalError, \
                   JsonRpcMethodNotFoundError, JsonRpcInvalidParamsError

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
        method_name = self.request.method
        params = self.request.params
        method = getattr(self, method_name, None)
        logger.debug('Call request: method=%s, params=%s'
                      % (method_name, params))
        try:
            if not callable(method) or method_name.startswith('_'):
                data = {'method': method_name}
                raise JsonRpcMethodNotFoundError(data=data)

            args, kwargs = [], params
            if isinstance(params, (list, tuple)):
                args, kwargs = params, {}

            try:
                result = method(*args, **kwargs)
            except TypeError:
                data = {
                    'method': method_name,
                    'params': params
                }
                raise JsonRpcInvalidParamsError(data=data)
        except Exception as err:
            self._on_error(err)
        else:
            if result is not None:
                self._on_result(result)

    def _on_result(self, result):
        '''
        A callback method that dispatches the given result of a requested
        method to a client.
        '''
        logger.debug('Call request: result=%s' % result)
        self._handler.on_result(self.request, result)
        self._handled = True

    def _on_error(self, error):
        '''
        A callback method that dispatches the given error of a requested
        method to a client.
        '''
        logger.debug('Call request: error=%s' % error)
        self._handler.on_error(self.request, error)
        self._handled = True


class ParsingHTTPError(Exception):
    def __init__(self, code, message):
        Exception.__init__(self, (code, message))
        self.code = code
        self.message = message


class JsonRpcRequestHandler(asyncore.dispatcher):
    '''
    A class of Json-RPC request handlers.
    '''
    # The server software version
    server_version = 'JsonRPC2/%s' % VERSION

    # The supported version of the HTTP protocol
    protocol_version = 'HTTP/1.1'

    def __init__(self, sock, server, timeout=5):
        asyncore.dispatcher.__init__(self, sock)
        self.server = server
        self.path = '/'
        self.data = ''
        self._readable = True
        self._writable = False
        self.read_buffer = ''
        self.write_buffer = ''
        self.timeout = time.time() + timeout
        self.content_len = None

    def readable(self):
        return self._readable

    def writable(self):
        return self._writable or self.timeout < time.time()

    def handle_read(self):
        if self.content_len is None:
            self.read_buffer += self.recv(8192)

            try:
                if not self.parse_http_request(self.read_buffer):
                    # Failed to parse headers. Wait for next portion.
                    return
            except ParsingHTTPError as err:
                self._readable = False
                self.send_http_error(err.code, err.message)
                return
            except Exception as err:
                self.log_message('Exception: %s', err)
                self._readable = False
                self.send_http_error(500, 'Internal Server Error')
                return
        else:
            self.data += self.recv(8192)

        if len(self.data) < self.content_len:
            return
        elif len(self.data) > self.content_len:
            self.data = self.data[:self.content_len]

        self._readable = False
        request = None
        try:
            request = loads(self.data, [JsonRpcNotification, JsonRpcRequest],
                            encoding=self.server.encoding)
            method = self.server.interface(self.server, request, self)
            method()
        except Exception as err:
            self.on_error(request, err)
        finally:
            if isinstance(request, JsonRpcNotification):
                self.close()

    def handle_write(self):
        if not self._writable:
            # Triggered by timeout.
            self.write_buffer = ''
            self.send_http_error(408, 'Request timed out')
        num_sent = 0
        num_sent = asyncore.dispatcher.send(self, self.write_buffer)
        self.write_buffer = self.write_buffer[num_sent:]
        if not self.write_buffer:
            self.close()

    def log_message(self, format, *args):
        logger.debug(format % args)

    def on_result(self, request, result):
        if isinstance(request, JsonRpcNotification):
            return
        response = JsonRpcResponse(request.id, result)
        data = response.dumps(encoding=self.server.encoding)
        self.send_http_result(data)

    def on_error(self, request, error):
        if isinstance(request, JsonRpcNotification):
            return
        if not isinstance(error, JsonRpcError):
            data = {'exception': '%s' % error}
            error = JsonRpcInternalError(data=data)
        if request:
            error.id = request.id
        data = dumps(error.marshal(), encoding=self.server.encoding)
        self.send_http_result(data)

    def parse_http_request(self, request_string):
        if not request_string:
            return False

        parts = request_string.split('\r\n', 1)
        words = parts[0].split()
        if not words:
            return False

        if len(words) != 3:
            raise ParsingHTTPError(400, 'Bad request syntax')

        command, self.path, version = words
        if version not in ('HTTP/1.0', 'HTTP/1.1'):
            raise ParsingHTTPError(400, 'Bad request version')

        self.protocol_version = version
        if command != 'POST':
            raise ParsingHTTPError(501, 'Unsupported method')

        if len(parts) < 2:
            return False

        parts = parts[1].split('\r\n\r\n')

        if len(parts) < 2:
            return False

        self.headers = email.message_from_string(parts[0])

        self.content_len = int(self.headers.get('content-length', 0))
        self.data = parts[1]
        return True

    def send_http_result(self, data):
        self.add_base_response(200, 'OK')
        self.add_content(data, 'application/json-rpc')
        self.log_message('"%s" %s %s', self.path, '200', str(len(data)))
        self._writable = True

    def send_http_error(self, code, message):
        self.add_base_response(code, message)

        content = ("<head><title>Error response</title></head>"
                   "<body>"
                   "<h1>Error response</h1>"
                   "<p>Error code %(code)d.</p>"
                   "<p>Message: %(message)s.</p>"
                   "</body>") % {
            'code': code,
            'message': message
        }

        self.add_content(content, 'text/html')
        self.log_message('"%s" %s %s', self.path, code, str(len(content)))
        self._writable = True

    def add_base_response(self, code, message):
        self.write_buffer += "%s %d %s\r\n" % \
                             (self.protocol_version, code, message)
        self.add_header('Server', self.server_version)
        self.add_header('User-Agent', 'Python-JsonRPC2')
        self.add_header(
            'Date', time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()))
        self.add_header('Connection', 'close')

    def add_header(self, keyword, value):
        self.write_buffer += "%s: %s\r\n" % (keyword, value)

    def add_content(self, content='', content_type=''):
        if content_type:
            self.add_header("Content-Type", content_type)

        if content:
            self.add_header('Content-Length', str(len(content)))

        self.write_buffer += "\r\n%s" % content


class JsonRpcServer(asyncore.dispatcher):
    '''
    A class of Json-RPC servers.
    '''
    #: A class of Json-RPC request handlers
    handler_class = JsonRpcRequestHandler

    def __init__(self, address, interface, timeout=5,
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
            self.set_reuse_addr()
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
            sock, address = accept_result
            if self.allowed_ips is None or address[0] in self.allowed_ips:
                logger.debug('Handle client: %s:%d' % address)
                self.handler_class(sock, self, timeout=self.timeout)
            else:
                logger.debug('Rejecting connection from: %s:%d' % address)
                sock.close()

    def handle_error(self):
        logger.exception('Unhandled server error')

    def handle_close(self):
        '''
        Closes the Json-RPC server.
        '''
        logger.info('Handle close server')
        self.close()
