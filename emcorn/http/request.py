import io
import sys
from urllib.parse import unquote

import emcorn
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
        self.fp = sock.makefile('rw', self.CHUNK_SIZE)

    def read(self):
        try:
            self.first_line(self.fp.readline())
        except RequestError:
            return {}

        self.read_headers()

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

    def read_headers(self):
        hname = ''
        while True:
            line = self.fp.readline()
            if line in ('\r\n', '\n', ''):
                break
            
            if line == '\t':
                self.headers[hname] += line.strip()
            else:
                try:
                    hname = self.parse_header(line)
                except ValueError:
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
            line = self.fp.readline().strip().split(';', 1)
            chunk_size = int(line.pop(0), 16)
            if chunk_size <= 0:
                break
            length += chunk_size

            data.write(self.fp.read(chunk_size))
            
            crlf = self.fp.read(2)
            if crlf != '\r\n':
                raise RequestError((400, "Bad chunked transfer coding (expected '\\r\\n', got %r)" % crlf))
                return
        
        self.read_headers()
        
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
        
        self.fp.write("%s\r\n\r\n" % "\r\n".join(res_headers))

    def write(self, data):
        self.fp.write(data)
    
    def close(self):
        self.fp.close()
        if self.should_close():
            self.socket.close()

    def first_line(self, line):
        if not line:
            raise RequestError(400, '')
        
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
    def __init__(self, request):
        self.length = request.body_length()
        self.fp = request.fp
        self.eof = False

    def close(self):
        self.eof = False
    
    def read(self, amt=None):
        if self.fp is None or self.eof:
            return ''
        
        if amt is None:
            s = self._safe_read(self.length)
            self.close()
            return s
        
        if amt > self.length:
            amt = self.length
        
        s = self.fp.read(amt)
        self.length -= len(s)
        if not self.length:
            self.close()
        
        return s

    def readline(self, size=None):
        if self.fp is None or self.eof:
            return ''
        
        if size is not None:
            data = self.fp.read(size)
        else:
            res = []
            while True:
                data = self.fp.read(256)
                res.append(data)
                if len(data) < 256 or data[-1:] == '\n':
                    data = ''.join(res)
                    break
            #end while True
        
        self.length -= len(data)
        if not self.length:
            self.close()
        
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

    def _safe_read(self, amt):
        s = []
        while amt > 0:
            chunk = self.fp.read(amt)
            if not chunk:
                raise RequestError((500, 'Incomplete read %s' % s))
            
            s.append(chunk)
            amt -= len(chunk)
        
        return ''.join(s)
    
    def __iter__(self):
        return self
    
    def next(self):
        if self.eof:
            raise StopIteration()
        return self.readline()
