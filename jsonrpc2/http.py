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
Definitions of HTTP helper classes for Json-RPC client side.
'''

import time
import socket
import httplib
import urllib
import urllib2
import asyncore

from . import logger

HTTP_HEADERS = {
    'Content-Type': 'application/json-rpc',
    'User-Agent': 'Python-JsonRPC2'
}

__metaclass__ = type

class HttpDispatcher(asyncore.dispatcher):
    '''
    A class of asynchronous HTTP response dispatchers.
    '''
    def __init__(self, sock, response):
        asyncore.dispatcher.__init__(self, sock)
        self.response = response

    def writable(self):
        if self._timeout and self._timeout < time.time():
            return True
        return False

    def set_timeout(self, timeout):
        '''
        Sets the given timeout for the response dispatcher.
        '''
        self._timeout = timeout and (timeout + time.time())

    def handle_read(self):
        logger.debug('Handle available response')
        # FIXME: Workaround for 'Resource temporarily unavailable' errors
        time.sleep(0.01)
        self.response.begin()
        try:
            if self.response.context:
                self.response.context.on_result()
        finally:
            if self.response.will_close:
                self.response.close()

    def handle_write(self):
        '''
        Handles a request timeout for the response dispatcher.
        '''
        logger.warning('Handle response time out')
        raise urllib2.URLError((110, 'Connection timed out'))

    def handle_error(self):
        logger.exception('Handle response error')
        error = asyncore.compact_traceback()[2]
        try:
            if self.response.context:
                self.response.context.on_error(error)
        finally:
            if self.response.will_close:
                self.response.close()


class HttpResponse(httplib.HTTPResponse):
    '''
    A class of asynchronous HTTP responses.
    '''
    usecount = 1

    def __init__(self, sock, method=None):
        httplib.HTTPResponse.__init__(self, sock, debuglevel=0,
                                      strict=1, method=method)
        self._dispatcher = HttpDispatcher(sock, self)
        self.context = None

    def connect(self, context, timeout=None):
        self.context = context
        self._dispatcher.set_timeout(timeout)

    def close(self):
        httplib.HTTPResponse.close(self)
        self._dispatcher.close()

    def _reuse(self):
        self.usecount += 1

    def _drop(self, space):
        self.usecount -= 1
        if self.usecount > 0:
            return
        self.close()

    recv = httplib.HTTPResponse.read


class HttpConnectionBase:
    '''
    A base class for HTTP connections.
    '''
    response_class = HttpResponse

    def getresponse(self):
        '''
        Based on httplib.HTTPConnection.getresponse().
        '''
        return self.response_class(self.sock, method=self._method)

class HttpConnection(HttpConnectionBase, httplib.HTTPConnection):
    '''
    A class of HTTP connections.
    '''
    __init__ = httplib.HTTPConnection.__init__

class HttpsConnection(HttpConnectionBase, httplib.HTTPSConnection):
    '''
    A class of HTTPS connections.
    '''
    __init__ = httplib.HTTPSConnection.__init__


class HttpHandlerBase:
    '''
    A base class for asynchronous HTTP request handlers.
    '''
    def do_open(self, connection_class, request):
        '''
        Based on urllib2.AbstractHTTPHandler.do_open().
        '''
        host = request.get_host()
        if not host:
            raise urllib2.URLError('no host given')

        connection = connection_class(host, timeout=request.timeout)
        connection.set_debuglevel(self._debuglevel)

        headers = dict(request.headers)
        headers.update(request.unredirected_hdrs)
        # We want to make an HTTP/1.1 request, but the addinfourl
        # class isn't prepared to deal with a persistent connection.
        # It will try to read all remaining data from the socket,
        # which will block while the server waits for the next request.
        # So make sure the connection gets closed after the (only)
        # request.
        headers['Connection'] = 'close'
        headers = dict((name.title(), val) for name, val in headers.iteritems())

        if request._tunnel_host:
            tunnel_headers = {}
            proxy_auth_hdr = 'Proxy-Authorization'
            if proxy_auth_hdr in headers:
                tunnel_headers[proxy_auth_hdr] = headers[proxy_auth_hdr]
                # Proxy-Authorization should not be sent to origin
                # server.
                del headers[proxy_auth_hdr]
            connection._set_tunnel(request._tunnel_host, headers=tunnel_headers)

        try:
            connection.request(request.get_method(), request.get_selector(),
                               request.data, headers)
        except socket.error as err: # XXX what error?
            raise urllib2.URLError(err)
        return connection.getresponse()

class HttpHandler(HttpHandlerBase, urllib2.HTTPHandler):
    '''
    A class of asynchronous HTTP request handlers.
    '''
    __init__ = urllib2.HTTPHandler.__init__

    def http_open(self, request):
        return self.do_open(HttpConnection, request)

class HttpsHandler(HttpHandlerBase, urllib2.HTTPSHandler):
    '''
    A class of asynchronous HTTPS request handlers.
    '''
    __init__ = urllib2.HTTPSHandler.__init__

    def https_open(self, request):
        return self.do_open(HttpsConnection, request)


class HttpRequestContext:
    '''
    A class of HTTP request contexts.
    '''
    _handler_classes = [
        urllib2.ProxyHandler,
        urllib2.HTTPDefaultErrorHandler,
        urllib2.HTTPRedirectHandler,
        HttpHandler,
        HttpsHandler
    ]

    def __init__(self, url, data, handler=None):
        self._request = urllib2.Request(url, data, HTTP_HEADERS)
        self._response = None
        self._on_result = None
        self._on_error = None
        # Connection opener
        self._opener = urllib2.OpenerDirector()
        self._processors = {}
        self._setup_opener(handler)

    def _setup_opener(self, handler=None):
        '''
        Sets up a corresponding HTTP connection opener.
        '''
        for handler_class in self._handler_classes:
            self._opener.add_handler(handler_class())
        if handler:
            self._opener.add_handler(handler)
        self._processors = self._opener.process_response
        self._opener.process_response = {}

    def _run(self, on_result=None, on_error=None, timeout=None):
        if on_result:
            self._on_result = on_result
        if on_error:
            self._on_error = on_error
        try:
            self._response = self._opener.open(self._request, timeout=timeout)
        except urllib2.URLError as err:
            self.on_error(err)
        else:
            self._response.connect(self, timeout=timeout)

    def closed(self):
        return self._response.isclosed() if self._response else True

    def on_result(self):
        if self._response is None:
            return
        fp = socket._fileobject(self._response, close=True)
        result = urllib.addinfourl(fp, self._response.msg,
                                   self._request.get_full_url())
        result.code = self._response.status
        result.msg = self._response.reason

        # Run response processors
        protocol = self._request.get_type()
        method_name = protocol + '_response'
        try:
            for processor in self._processors.get(protocol, []):
                method = getattr(processor, method_name)
                result = method(self.request, result)
                if result:
                    break
        except Exception as err:
            self.on_error(err)
        else:
            if self._on_result:
                self._on_result(result)

    def on_error(self, error):
        if self._on_error:
            self._on_error(error)

