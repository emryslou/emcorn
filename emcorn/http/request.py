import io
import sys
from urllib.parse import unquote

import emcorn
from emcorn.http.iostream import IOStream
from .errors import RequestError
logger = emcorn.logging.log

class HttpRequest(object):
    
    SERVER_VERSION = 'emcorn/%s' % emcorn.__version__
    CHUNK_SIZE = 4096

    def __init__(self, sock, client_address, server_address):
        self.socket = sock
        self.client = client_address
        self.server = server_address

        self.version = None
        self.method = None
        self.path = None
        self.headers = {}
        self.response_status = None
        self.response_headers = {}

        self._version = 11
        self.io = IOStream(self.socket)
        self.start_response_called = False

    def read(self):
        self.read_headers(first_line = True)

        if '?' in self.path:
            path_info, query = self.path.split('?', 1)
        else:
            path_info, query = self.path, ''
        
        length = self.body_length()
        if not length:
            wsgi_input = io.StringIO()
        elif length == 'chunked':
            length, wsgi_input = self.decode_chunked()
        else:
            wsgi_input = FileInput(self)
        
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
            "REQUEST_METHOD": self.method,
            "PATH_INFO": unquote(path_info),
            "QUERY_STRING": query,
            "RAW_URI": self.path,
            "CONTENT_TYPE": self.headers.get('content-type', ''),
            "CONTENT_LENGTH": length,
            "REMOTE_ADDR": self.client[0],
            "REMOTE_PORT": self.client[1],
            "SERVER_NAME": self.server[0],
            "SERVER_PORT": self.server[1],
            "SERVER_PROTOCOL": self.version
        }

        for key, value in self.headers.items():
            key = 'HTTP_' + key.replace('-', '_')
            if key not in ('HTTP_CONTENT_TYPE', 'HTTP_CONTENT_LENGTH'):
                environ[key] = value
        return environ

    def read_headers(self, first_line = False):
        headers_body = self.io.read_until('\r\n\r\n')
        lines = headers_body.split('\r\n')
        if first_line:
            self.first_line(lines.pop(0))
        hname = ''
        for line in lines:
            if line == '\t':
                self.headers[hname] += line.strip()
            else:
                try:
                    hname = self.parse_header(line)
                except:
                    pass

    def body_length(self):
        transfert_encoding = self.headers.get('TRANSFERT-ENCODING', None)
        content_length = self.headers.get('CONTENT-LENGHT', None)

        if transfert_encoding is None:
            return content_length
        elif transfert_encoding == 'chunked':
            return transfert_encoding
        else:
            return None

    def should_close(self):
        if self.headers.get('CONNECTION') == 'close':
            return True
        
        if self.headers.get('CONNECTION') == 'Keep-Alive':
            return False
        

        if not self.version or self.version < 'HTTP/1.1':
            return True
    
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
        res_headers = []
        self.response_status = status
        self.response_headers = {}

        res_headers.append('%s %s' % (self.version, status))
        for name, value in headers:
            res_headers.append('%s: %s' % (name, value))
            self.response_headers[name.lower()] = value
        
        headers = "%s\r\n\r\n" % "\r\n".join(res_headers)
        self.io.send(headers.encode())
        self.start_response_called = True

    def write(self, data):
        self.io.send(data)
    
    def close(self):
        if self.should_close():
            self.socket.close()

    def first_line(self, line):
        if not line:
            raise RequestError(400, 'Bad Request')
        
        method, path, version = line.split(' ')
        self.version = version.strip()
        self.method = method.upper()
        self.path = path
        
    
    def parse_header(self, line):
        name, value = line.split(':', 1)
        name = name.strip().upper()
        
        self.headers[name] = value.strip()
        
        return name


class FileInput(object):
    stream_size = 4096

    def __init__(self, request):
        self.length = request.body_length()
        self.io = request.io
        self._rbuf = ''

    def close(self):
        self.eof = False
    
    def read(self, amt=None):
        if self._rbuf and not amt is None:
            L = len(self._rbuf)
            if amt > L:
                amt -= L
            else:
                s = self._rbuf[:amt]
                self._rbuf = self._rbuf[amt:]
                return s
            
            data = self.io.recv(amt)
            s = self._rbuf + data
            self._rbuf = ''

            return s

    def readline(self, amt = -1):
        i = self._rbuf.find('\n')
        while i < 0 and not(0 < amt <= len(self._rbuf)):
            new = self.io.recv(self.stream_size)
            if not new:
                break
            i = new.find('\n')
            if i > 0:
                i += len(self._rbuf)
            self._rbuf = self._rbuf + new
        if i < 0:
            i = len(self._rbuf)
        else:
            i += 1
        
        if 0 < amt <= len(self._rbuf):
            i = amt
        
        data, self._rbuf = self._rbuf[:i], self._rbuf[i:]
        return data

    def readlines(self, sizehint=0):
        total = 0
        lines = []
        
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
            total += len(line)
            if 0 < sizehint <= total:
                break
        
        return lines
    
    def __iter__(self):
        return self
    
    def next(self):
        r = self.readline()
        if not r:
            raise StopIteration()
        
        return r
