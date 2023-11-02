import ctypes
import sys
from urllib.parse import urlsplit

from emcorn.http.exceptions import HttpParserError, ParseFirstLineError
from emcorn.logging import log
from emcorn.util import normalize_name


class HttpParser(object):
    def __init__(self):
        self._headers = []
        self._headers_dict = {}

        self.status = ''
        self.raw_version = ''
        self.raw_path = ''

        self.version = None
        self.method = ""
        self.path = ""
        self.query_string = ""
        self.fragment = ""

        self._content_len = None
        self.start_offset = 0
        self.chunk_size = 0
        self._chunk_eof = False
    
    def filter_headers(self, headers, buf):
        if self._headers:
            return self._headers
        
        ld = len('\r\n\r\n')
        i = buf.find('\r\n\r\n')
        if i > 0:
            r = buf[:i]            
            return self.finalize_headers(headers, r, i + ld)
        
        return -1
    
    def finalize_headers(self, headers, r, pos):
        lines = r.split('\r\n')
        self._first_line(lines.pop(0))
        _headers = {}
        hname = ''
        for line in lines:
            if line == '\t':
                _headers[hname] += line.strip()
            else:
                try:
                    hname = self.parse_header(_headers, line)
                except:
                    pass
        
        self._headers_dict = _headers
        headers.extend(list(_headers.items()))

        self._headers = headers
        self._content_len = int(_headers.get('Content-Length') or 0)

        _, _, self.path, self.query_string, self.fragment = urlsplit(self.raw_path)
        return pos

    
    def _first_line(self, line):
        if not line:
            raise ParseFirstLineError(400, 'Bad Request: first line none')
        
        self.status = status = line.strip()
        
        method, path, version = status.split(' ')
        version = version.strip()
        self.raw_version = version
        try:
            major, minor = version.split('HTTP/')[1].split('.')
            version = (int(major), int(minor))
        except IndexError:
            version = (1, 0)

        self.version = version
        self.method = method.upper()
        self.raw_path = path

    def parse_header(self, headers, line):
        name, value = line.split(':', 1)
        name = normalize_name(name.strip())
        
        headers[name] = value.rsplit("\r\n", 1)[0].strip()
        
        return name
    
    @property
    def should_close(self):
        # if self._should_close:
        #     return True
        
        if self._headers_dict.get('CONNECTION') == 'close':
            return True
        
        if self._headers_dict.get('CONNECTION') == 'Keep-Alive':
            return False
        

        if not self.version or self.version < 'HTTP/1.1':
            return True
    
    @property
    def is_chunked(self):
        transfer_encoding = self._headers_dict.get('Transfer-Encoding', '')
        return transfer_encoding == 'chunked'
    
    @property
    def content_length(self):
        transfer_encoding = self._headers_dict.get('Transfer-Encoding', None)
        content_length = self._headers_dict.get('Content-Length', None)

        if transfer_encoding is None:
            return int(content_length or '0')
        else:
            return None
    
    def body_eof(self):
        #todoL add chunk
        if self.is_chunked:
            if self._chunk_eof:
                return True
        elif self._content_len == 0:
            return True

        return False
    
    def read_chunk(self, data):
        dlen = len(data)
        if not self.start_offset:
            i = data.find('\r\n')
            if i != -1:
                chunk = data[:i].strip().split(";", 1)
                chunk_size = int(chunk.pop(0), 16)
                self.chunk_size = chunk_size
                self.start_offset = i + 2
                if self.chunk_size == 0:
                    self._chunk_eof = True
                    return '', data[:self.start_offset]
        else:
            buf = data[self.start_offset:self.start_offset + self.chunk_size]
            end_offset = self.start_offset + self.chunk_size + 2
            if len(data) >= end_offset:
                ret = buf, data[end_offset:]
                self.chunk_size = 0
                return ret
        
        return '', data
    
    def trailing_header(self, data):
        i = data.find('\r\n\r\n')
        return i != -1

    def filter_body(self, data):
        dlen = len(data)
        chunk = ''
        if self.is_chunked:
            chunk, data = self.read_chunk(data)
            if not chunk:
                return '', data
        else:
            if self._content_len > 0:
                nr = min(dlen, self._content_len)
                chunk = data[:nr]
                self._content_len -= nr

                data = ''
        
        self.start_offset = 0
        return chunk, data
