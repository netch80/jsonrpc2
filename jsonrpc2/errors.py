class JsonRpcError(Exception):
    '''
    A base class of Json-RPC errors
    '''
    def __init__(self, code=32000, message='JSON-RPC error.',
                      id=None, data=None):
        if code > 0:
            code = -code
        Exception.__init__(self, (code, message))
        self.id = id
        self.code = code
        self.message = message
        self.data = data

    def marshal(self):
        error = {
            'code': self.code,
            'message': self.message
        }
        if self.data:
            error['data'] = self.data
        return {
            'error': error,
            'id': self.id
        }


# Standard errors:

class JsonRpcParseError(JsonRpcError):
    def __init__(self, data=None):
        JsonRpcError.__init__(self, 32700, 'Parse error.', data=data)

class InvalidJsonRpcError(JsonRpcError):
    def __init__(self, data=None):
        JsonRpcError.__init__(self, 32600, 'Invalid JSON-RPC.', data=data)

class JsonRpcMethodNotFoundError(JsonRpcError):
    def __init__(self, id=None, data=None):
        JsonRpcError.__init__(self, 32601, 'Method not found.', id, data=data)

class JsonRpcInvalidParamsError(JsonRpcError):
    def __init__(self, id=None, data=None):
        JsonRpcError.__init__(self, 32602, 'Invalid params.', id, data=data)

class JsonRpcInternalError(JsonRpcError):
    def __init__(self, id=None, data=None):
        JsonRpcError.__init__(self, 32603, 'Internal error.', id, data=data)

