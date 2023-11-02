import ctypes

from emcorn.logging import log
from .exceptions import ParseFirstLineError


class HttpParser(object):
    def __init__(self):
        self._headers = {}
        self.version = None
        self.method = None
        self.path = None
        self._content_len = None
    
    def headers(self, headers, buf):
        if self._headers:
            return self._headers
        if isinstance(buf, ctypes.Array):
            buf = buf.value.decode()
        
        ld = len('\r\n\r\n')
        i = buf.find('\r\n\r\n')
        if i > 0:
            r = buf[:i]
            # buf = ctypes.create_string_buffer(cs[i+ld:])
            return self.finalize_headers(headers, r, i + ld)
        
        return -1
    
    def finalize_headers(self, headers, r, pos):
        lines = r.split('\r\n')
        self._first_line(lines.pop(0))

        hname = ''
        for line in lines:
            if line == '\t':
                self._headers[hname] += line.strip()
            else:
                try:
                    hname = self.parse_header(line)
                except:
                    pass
        
        headers.update(self._headers)

        self._content_len = int(self._headers.get('Content-Length') or 0)
        
        return pos

    
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
        
        self._headers[name] = value.strip()
        
        return name
    
    @property
    def should_close(self):
        # if self._should_close:
        #     return True
        
        if self._headers.get('CONNECTION') == 'close':
            return True
        
        if self._headers.get('CONNECTION') == 'Keep-Alive':
            return False
        

        if not self.version or self.version < 'HTTP/1.1':
            return True
    
    @property
    def is_chunked(self):
        transfer_encoding = self._headers.get('Transfer-Encoding', '')
        return transfer_encoding == 'chunked'
    
    @property
    def content_length(self):
        transfer_encoding = self._headers.get('Transfer-Encoding', None)
        content_length = self._headers.get('Content-Length', None)

        if transfer_encoding is None:
            return int(content_length or '0')
        else:
            return None
    
    def body_eof(self):
        #todoL add chunk
        return self._content_len == 0
    
    def read_chunk(self, data):
        dlen = len(data)
        i = data.find('\n')
        if i == -1:
            return None

        chunk = data[:i].strip().split(";", 1)
        chunk_size = int(chunk.pop(0), 16)
        if chunk_size <= 0:
            self._chunk_eof = True
            return None
        self.start_offset = i + 1
        return data
    
    def filter_body(self, data):
        dlen = len(data)
        chunk = None
        if self.is_chunked:
            pass
        else:
            if self._content_len > 0:
                nr = min(dlen, self._content_len)
                chunk = data[:nr]
                self._content_len -= nr

                data = None
        
        self.start_offset = 0
        return chunk, data
