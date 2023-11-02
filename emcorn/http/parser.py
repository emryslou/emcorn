import ctypes

from emcorn.logging import log
from .exceptions import ParseFirstLineError


class HttpParser(object):
    def __init__(self):
        self.headers = {}
        self.version = None
        self.method = None
        self.path = None
        self._content_len = None
    
    def header(self, headers, buf):
        if isinstance(buf, ctypes.Array):
            buf = buf.value.decode()
        
        cs = ''.join(buf)
        ld = len('\r\n\r\n')
        i = cs.find('\r\n\r\n')
        if i > 0:
            r = cs[:i]
            # buf = ctypes.create_string_buffer(cs[i+ld:])
            return self.finalize_headers(headers, r)
        
        return None
    
    def finalize_headers(self, headers, r):
        lines = r.split('\r\n')
        self._first_line(lines.pop(0))

        hname = ''
        for line in lines:
            if line == '\t':
                self.headers[hname] += line.strip()
            else:
                try:
                    hname = self.parse_header(line)
                except:
                    pass
        
        headers = self.headers

        _content_len = self.headers.get('Content-Length', None)
        self._content_len = int(_content_len) if _content_len is not None else None
        
        
        return headers

    
    def _first_line(self, line):
        if not line:
            raise ParseFirstLineError(400, 'Bad Request: first line none')
        
        method, path, version = line.split(' ')
        self.version = version.strip()
        self.method = method.upper()
        self.path = path

    def parse_header(self, line):
        name, value = line.split(':', 1)
        name = name.strip().upper()
        
        self.headers[name] = value.strip()
        
        return name
    
    @property
    def should_close(self):
        # if self._should_close:
        #     return True
        
        if self.headers.get('CONNECTION') == 'close':
            return True
        
        if self.headers.get('CONNECTION') == 'Keep-Alive':
            return False
        

        if not self.version or self.version < 'HTTP/1.1':
            return True
    
    @property
    def is_chunked(self):
        transfer_encoding = self.headers.get('Transfer-Encoding', '')
        return transfer_encoding == 'chunked'
    
    @property
    def content_length(self):
        transfer_encoding = self.headers.get('Transfer-Encoding', None)
        content_length = self.headers.get('Content-Length', None)

        if transfer_encoding is None:
            return int(content_length or '0')
        else:
            return None
    
    def body_eof(self):
        #todoL add chunk
        return self._content_len == 0
    
    def fetch_body(self, buf, data):
        dlen = len(data)
        ctypes.resize(buf, ctypes.sizeof(data))
        if self.is_chunked:
            # todo: chunk
            pass
        else:
            if self._content_len > 0:
                nr = min(len(data), self._content_len)

                ctypes.memmove(ctypes.addressof(buf), ctypes.addressof(data))

                self._content_len -= nr

                data.value = None
                ctypes.resize(buf, nr)
        
        self.start_offset = 0
        return data
