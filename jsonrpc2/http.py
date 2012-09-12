import socket
import httplib
import urllib
import urllib2
import asyncore

HTTP_HEADERS = {
    'Content-Type': 'application/json-rpc',
    'User-Agent': 'Python-JsonRPC2'
}

__metaclass__ = type

class HttpDispatcher(asyncore.dispatcher):
    def __init__(self, sock, response):
        asyncore.dispatcher.__init__(self, sock)
        self.response = response

    def handle_read(self):
        self.response.begin()
        try:
            if self.response.context:
                self.response.context.on_result()
        finally:
            if self.response.will_close:
                self.response.close()

    def handle_error(self):
        error = asyncore.compact_traceback()[2]
        try:
            if self.response.context:
                self.response.context.on_error(error)
        finally:
            if self.response.will_close:
                self.response.close()


class HttpResponse(httplib.HTTPResponse):
    def __init__(self, sock, debuglevel=0, strict=0, method=None):
        httplib.HTTPResponse.__init__(self, sock, debuglevel=debuglevel,
                                      strict=strict, method=method)
        self._dispatcher = HttpDispatcher(sock, self)
        self.context = None

    def connect(self, context):
        self.context = context

    def close(self):
        httplib.HTTPResponse.close(self)
        self._dispatcher.close()

    recv = httplib.HTTPResponse.read


class HttpConnectionBase:
    response_class = HttpResponse
    
    def getresponse(self):
        '''
        Based on httplib.HTTPConnection.getresponse().
        '''
        return self.response_class(self.sock, self.debuglevel,
                                   strict=self.strict, method=self._method)

class HttpConnection(HttpConnectionBase, httplib.HTTPConnection):
    __init__ = httplib.HTTPConnection.__init__

class HttpsConnection(HttpConnectionBase, httplib.HTTPSConnection):
    __init__ = httplib.HTTPSConnection.__init__


class HttpHandlerBase:
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
        except socket.error, err: # XXX what error?
            raise urllib2.URLError(err)
        return connection.getresponse()

class HttpHandler(HttpHandlerBase, urllib2.HTTPHandler):
    __init__ = urllib2.HTTPHandler.__init__

    def http_open(self, request):
        return self.do_open(HttpConnection, request)

class HttpsHandler(HttpHandlerBase, urllib2.HTTPSHandler):
    __init__ = urllib2.HTTPSHandler.__init__

    def https_open(self, request):
        return self.do_open(HttpsConnection, request)


class HttpRequestContext:
    def __init__(self, url, data, handler=None):
        self._request = urllib2.Request(url, data, HTTP_HEADERS)
        self._response = None
        self._on_result = None
        self._on_error = None
        # Build opener
        opener = urllib2.build_opener(HttpHandler(), HttpsHandler())
        if handler:
            opener.add_handler(handler)
        self._processors = opener.process_response
        opener.process_response = {}
        self._opener = opener

    def _run(self, on_result=None, on_error=None, timeout=None):
        if on_result:
            self._on_result = on_result
        if on_error:
            self._on_error = on_error
        self._response = self._opener.open(self._request, timeout=timeout)
        self._response.connect(self)

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
        for processor in self._processors.get(protocol, []):
            method = getattr(processor, method_name)
            result = method(self.request, result)

        if self._on_result:
            self._on_result(result)

    def on_error(self, error):
        if self._response is None:
            return
        if self._on_error:
            self._on_error(error)

