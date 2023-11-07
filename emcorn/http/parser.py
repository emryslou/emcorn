from logger import logger as log
from exceptions import HttpParseError
class HttpParser(object):
    def __init__(self, sock, debug: bool = False):
        self.debug = debug
        self.bufsize = 1024
        self.buf = b''
        self.sock = sock

        self.method = ''
        self.query = ''
        self.version = (0, 9)
        self.headers = []
        self.headers_dict = {}
    
    def parse(self):
        self._parse_first_line()
        self._parse_headers()

    def _parse_first_line(self):
        line = b''
        while True:
            buf = self.sock.recv(self.bufsize)
            if not buf:
                # may be wait some times
                raise HttpParseError(reason='Request Body Empty')
            
            idx = buf.index(b'\r\n')
            if idx > 0:
                line += buf[:idx]
                self.buf = buf[idx+2:]
                break
            elif idx == 0:
                raise HttpParseError(reason='First Line of Request Body is empty')
            else:
                line += buf
        method, query, version = line.decode().strip().split(' ', 3)
        self.method = method
        self.query = query
        self.version = tuple(version.replace('HTTP/', '').split('.'))
        # log.info(f'buf: {self.buf}')

    def _parse_headers(self):
        while self.buf:
            idx = self.buf.index(b'\r\n')
            if idx == -1:
                self.buf += self.sock.recv(self.bufsize)
            elif idx == 0:
                break
            else:
                header_buf = self.buf[:idx]
                self.buf = self.buf[idx + 2:]
                header_name, header_value = header_buf.decode().strip().split(': ', 2)
                self.headers.append((header_name, header_value))
                self.headers_dict[header_name] = header_value