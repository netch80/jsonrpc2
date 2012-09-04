import json
import urllib2

from base import _gen_id
from errors import JsonRpcError
from http import HttpRequestContext

__metaclass__ = type

def dumps(method, params, id=None, encoding=None):
    if id is None:
        id = _gen_id()
    if not encoding:
        encoding = 'utf-8'
    data = {
        'jsonrpc': '2.0',
        'method': method,
        'params': params,
        'id': id
    }
    return json.dumps(data, encoding=encoding)

def loads(data, id, encoding=None):
    if not encoding:
        encoding = 'utf-8'
    return json.loads(data, encoding=encoding)

class JsonRpcRequest(urllib2.Request):
    #: Default Json-RPC headers
    _headers = {
        'Content-Type': 'application/json-rpc',
        'User-Agent': 'Python-JsonRPC2'
    }

    def __init__(self, url, method, params, encoding=None):
        self.id = _gen_id()
        self.method = method
        self.params = params
        self.encoding = encoding
        data = dumps(method, params, self.id, encoding)
        urllib2.Request.__init__(self, url, data, self._headers)


class JsonRpcMethod:
    def __init__(self, name, server):
        self.name = name
        self.server = server

    def __call__(self, params, on_result=None, on_error=None):
        return self.server.request(self.name, params, on_result, on_error)


class JsonRpcProcessor(urllib2.BaseHandler):
    handler_order = 9999

    def http_response(self, request, response):
        print request
        if response.code == 200:
            response = loads(response.read(), request.id)
        return response

    https_response = http_response


class JsonRpcClient:
    #: Default HTTP path
    _http_path = '/RPC2'

    def __init__(self, url, timeout=None, encoding=None):
        self.url = url
        self.timeout = timeout
        self.encoding = encoding or 'utf-8'

    def __getattr__(self, method):
        return JsonRpcMethod(method, self)

    def request(self, method, params, on_result=None, on_error=None):
        request = JsonRpcRequest(self.url, method, params, self.encoding)
        context = HttpRequestContext(request, JsonRpcProcessor())
        context.run(on_result, on_error, self.timeout)
        return context

