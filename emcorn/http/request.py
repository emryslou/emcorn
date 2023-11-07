import socket
from urllib.parse import unquote
from http.parser import HttpParser
from logger import logger as log

class HttpRequest(object):
    def __init__(self, sock: socket.socket, request_time, client, server, debug: bool = False):
        self.bufsize = 1024
        self.__attr_cache = {}

        self.sock: socket.socket = sock
        self.request_time = request_time
        self.client = client
        self.server = server

        self.parser = HttpParser(sock, debug)

        self._environ = {}

        self.buf = b''
    
    def send(self, data: bytes):
        self.sock.send(data)
    
    def environ(self):
        if self._environ:
            return self._environ
        
        self.parser.parse()
        self._environ['REQUEST_METHOD'] = self.parser.method
        self._environ['SCRIPT_NAME'] = ''
        self._environ['PATH_INFO'] = unquote(self.parser.query)
        self._environ['SERVER_PROTOCOL'] = 'HTTP/%s.%s' % (self.parser.version[0], self.parser.version[1])
        self._environ['QUERY_STRING'] = '' if '?' not in self.parser.query else self.parser.query.split('?', 1)[1]
        self._environ['REQUEST_TIME'] = self.request_time
        for key, value in self.parser.headers:
            key = 'HTTP_%s' % (key.upper().replace('-', '_'))
            self._environ[key]  = value
        return self._environ

    def keep_alive(self):
        _keep_alive = self.__attr_cache.get('keep_alive', None)
        if _keep_alive is not None:
            return _keep_alive

        _keep_alive = self.parser.headers_dict.get('Connection', '').lower() == 'keep-alive' 
        self.__attr_cache['keep_alive'] = _keep_alive
        return _keep_alive