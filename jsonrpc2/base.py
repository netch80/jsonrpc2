import json
import random
import string

from errors import JsonRpcError, JsonRpcParseError, InvalidJsonRpcError

VERSION = '2.0'

_ID_CHARSET = string.ascii_letters + string.digits

__metaclass__ = type

def _gen_id(length=8):
    return ''.join([random.choice(_ID_CHARSET) for i in xrange(length)])

def dumps(message, encoding=None):
    if not encoding:
        encoding = 'utf-8'
    message['jsonrpc'] = VERSION
    try:
        return json.dumps(message, encoding=encoding)
    except TypeError, err:
        data = {'exception': '%s' % err}
        raise JsonRpcParseError(data=data)

def loads(data, classes, encoding=None):
    if not encoding:
        encoding = 'utf-8'
    try:
        message = json.loads(data, encoding=encoding)
    except ValueError, err:
        data = {'exception': '%s' % err}
        raise JsonRpcParseError(data=data)
    # Basic JSON-RPC validation
    if not isinstance(message, dict) or message.pop('jsonrpc', None) != VERSION:
        raise InvalidJsonRpcError()
    # JSON-RPC message validation
    for cls in classes:
        try:
            return cls(**message)
        except TypeError:
            pass
    try:
        raise JsonRpcError(**message)
    except TypeError, err:
        data = {'exception': '%s' % err}
        raise JsonRpcParseError(data=data)


class JsonRpcBase:
    def dumps(self, message, encoding=None):
        return dumps(message, encoding=encoding)

class JsonRpcNotification(JsonRpcBase):
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
    def __init__(self, id, result):
        self.id = id
        self.result = result

    def dumps(self, encoding=None):
        response = {
            'result': self.result,
            'id': self.id
        }
        return JsonRpcBase.dumps(self, response, encoding=encoding)

