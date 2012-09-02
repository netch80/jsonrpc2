import json
import urllib2

from http import HttpRequestContext

__metaclass__ = type

PROTOCOL_VERSION = '2.0'

_id = 0

def _get_id():
    global _id
    _id += 1
    return _id

def dumps(method, params, id=None, encoding=None):
    if id is None:
        id = _get_id()
    if not encoding:
        encoding = 'utf-8'
    data = {
        'jsonrpc': PROTOCOL_VERSION,
        'method': method,
        'params': params,
        'id': id
    }
    return json.dumps(data, encoding=encoding)

def loads(data, encoding=None):
    if not encoding:
        encoding = 'utf-8'
    return json.loads(data, encoding=encoding)


class JsonRpcError(Exception):
    '''
    A base class of Json-RPC errors
    '''
    pass


class JsonRpcHttpError(JsonRpcError):
    '''
    An exception class for representing Json-RPC HTTP transport errors.
    '''
    def __init__(self, url, code, msg, headers):
        JsonRpcError.__init__(self)
        self.url = url
        self.code = code
        self.msg = msg
        self.headers = headers

    def __repr__(self):
        return '<%s for %s: %s %s>' % (self.url, self.code, self.msg)


class JsonRpcMethod:
    def __init__(self, name, server):
        self.name = name
        self.server = server

    def __call__(self, params, on_result=None, on_error=None):
        return self.server.request_method(self.name, params,
                                          on_result, on_error)


class JsonRpcProcessor(urllib2.BaseHandler):
    handler_order = 9999

    def http_response(self, request, response):
        if response.code == 200:
            response = loads(response.read())
        return response

    https_response = http_response


class JsonRpcClient:
    #: Default HTTP path
    _http_path = '/RPC2'

    #: Default HTTP headers
    _http_headers = {
        'Content-Type': 'application/json-rpc',
        'User-Agent': 'Python-JsonRPC2'
    }

    def __init__(self, url, timeout=None, encoding=None):
        self.url = url
        self.timeout = timeout
        self.encoding = encoding or 'utf-8'

    def __getattr__(self, method):
        return JsonRpcMethod(method, self)

    def request_method(self, method, params, on_result=None, on_error=None):
        data = dumps(method, params, encoding=self.encoding)
        context = HttpRequestContext(self.url, data, self._http_headers,
                                     JsonRpcProcessor())
        context.run(on_result, on_error)
        return context

