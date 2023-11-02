import ctypes
import io
import re
import sys
from urllib.parse import unquote

import emcorn
from emcorn.http.parser import HttpParser
from emcorn.http.tee import TeeInput
from emcorn.util import CHUNK_SIZE
from .exceptions import RequestError
logger = emcorn.logging.log

def _normalize_name(name):
    return '-'.join([w.lower().capitalize() for w in name.split('-')])

class HttpRequest(object):
    
    SERVER_VERSION = 'emcorn/%s' % emcorn.__version__

    def __init__(self, sock, client_address, server_address):
        self.socket = sock.dup()
        self.client = client_address
        self.server = server_address

        self.response_status = None
        self.response_headers = {}

        self._version = 11
        self.parser = HttpParser()
        self.start_response_called = False

    def read(self):
        headers = {}
        remain = CHUNK_SIZE
        buf = ctypes.create_string_buffer(remain)
        remain -= self.socket.recv_into(buf, remain)

        while not self.parser.headers(headers, buf):
            data = ctypes.create_string_buffer(remain)
            remain -= self.socket.recv_into(data, remain)
            buf = ctypes.create_string_buffer(data.value + buf.value)
        
        if headers.get('Except', '').lower() == '100-continue':
            self.socket.send('100 Continue\n')

        if '?' in self.parser.path:
            path_info, query = self.parser.path.split('?', 1)
        else:
            path_info, query = self.parser.path, ''
        
        if not self.parser.content_length and not self.parser.is_chunked:
            wsgi_input = io.StringIO()
        else:
            wsgi_input = TeeInput(self.socket, self.parser, buf, remain)
        
        environ = {
            "wsgi.url_scheme": 'http',
            "wsgi.input": wsgi_input,
            "wsgi.errors": sys.stderr,
            "wsgi.version": (1, 0),
            "wsgi.multithread": False,
            "wsgi.multiprocess": True,
            "wsgi.run_once": False,
            "SCRIPT_NAME": "",
            "SERVER_SOFTWARE": self.SERVER_VERSION,
            "REQUEST_METHOD": self.parser.method,
            "PATH_INFO": unquote(path_info),
            "QUERY_STRING": query,
            "RAW_URI": self.parser.path,
            "CONTENT_TYPE": headers.get('content-type', ''),
            "CONTENT_LENGTH": str(len(wsgi_input.getvalue())),
            "REMOTE_ADDR": self.client[0],
            "REMOTE_PORT": self.client[1],
            "SERVER_NAME": self.server[0],
            "SERVER_PORT": self.server[1],
            "SERVER_PROTOCOL": self.parser.version
        }

        for key, value in headers.items():
            key = 'HTTP_' + key.upper().replace('-', '_')
            if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
                environ[key] = value
        return environ

    def decode_chunked(self):
        length = 0
        data = io.StringIO()
        while True:
            line = self.io.read_until('\n').strip().split(';', 1)
            chunk_size = int(line.pop(0), 16)
            if chunk_size <= 0:
                break
            length += chunk_size

            data.write(self.io.recv(chunk_size))
            
            crlf = self.io.read(2)
            if crlf != '\r\n':
                raise RequestError((400, "Bad chunked transfer coding (expected '\\r\\n', got %r)" % crlf))
                return
        
        data.seek(0)
        return data, str(length) or ''

    def start_response(self, status, headers):
        self.response_status = int(status.split(" ")[0])
        self.response_headers = {}

        for name, value in headers:
            self.response_headers[name.lower()] = value
        
        self.start_response_called = True

    def write(self, data):
        self.req.socket.send(data)
    
    def close(self):
        self.socket.close()
