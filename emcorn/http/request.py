import ctypes
import io
import re
import sys
from urllib.parse import unquote

import emcorn

from emcorn.http._type import StringIO
from emcorn.http.exceptions import RequestError
from emcorn.http.parser import HttpParser
from emcorn.http.tee import TeeInput
from emcorn.util import CHUNK_SIZE, close, normalize_name, read_partial, write


logger = emcorn.logging.log

DEFAULT_ENVIRON = {
    "wsgi.url_scheme": 'http',
    "wsgi.input": StringIO(),
    "wsgi.errors": sys.stderr,
    "wsgi.version": (1, 0),
    "wsgi.multithread": False,
    "wsgi.multiprocess": True,
    "wsgi.run_once": False,
    "SCRIPT_NAME": "",
    "SERVER_SOFTWARE": 'emcorn/%s' % emcorn.__version__,
}


class HttpRequest(object):
    
    SERVER_VERSION = 'emcorn/%s' % emcorn.__version__

    def __init__(self, sock, client_address, server_address):
        self.socket = sock
        self.client = client_address
        self.server = server_address

        self.response_status = None
        self.response_headers = {}

        self._version = 11
        self.parser = HttpParser()
        self.start_response_called = False

    def read(self):
        environ = {}
        headers = []
        remain = CHUNK_SIZE

        buf = ''
        while True:
            data = read_partial(self.socket, CHUNK_SIZE)
            if not data:
                break
            buf += data.decode()
            i = self.parser.filter_headers(headers, buf)
            if i != -1:
                break
        
        if not buf:
            self.socket.close()
        
        if self.parser._headers_dict.get('Except', '').lower() == '100-continue':
            self.write('100 Continue\n')

        if '?' in self.parser.path:
            path_info, query = self.parser.path.split('?', 1)
        else:
            path_info, query = self.parser.path, ''
        
        if not self.parser.content_length and not self.parser.is_chunked:
            wsgi_input = StringIO()
        else:
            wsgi_input = TeeInput(self.socket, self.parser, buf[i:])
        
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
            "PATH_INFO": unquote(self.parser.path),
            "QUERY_STRING": self.parser.query_string,
            "RAW_URI": self.parser.raw_path,
            "CONTENT_TYPE": self.parser._headers_dict.get('content-type', ''),
            "CONTENT_LENGTH": str(wsgi_input.len),
            "REMOTE_ADDR": self.client[0],
            "REMOTE_PORT": self.client[1],
            "SERVER_NAME": self.server[0],
            "SERVER_PORT": self.server[1],
            "SERVER_PROTOCOL": self.parser.raw_version
        }

        for key, value in self.parser._headers:
            key = 'HTTP_' + key.upper().replace('-', '_')
            if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
                environ[key] = value
        return environ
    
    def start_response(self, status, headers):
        self.response_status = int(status.split(" ")[0])
        self.response_headers = {}

        for name, value in headers:
            name = normalize_name(name)
            self.response_headers[name] = value.strip()
        
        self.start_response_called = True

    def write(self, data):
        write(self.socket, data)
    
    def close(self):
        close(self.socket)
