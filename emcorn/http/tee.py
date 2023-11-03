import ctypes
import io
import os
import tempfile

from emcorn.util import MAX_BODY, CHUNK_SIZE, read_partial

class TeeInput(object):
    def __init__(self, socket, parser, buf):
        self.buf = buf
        self.parser = parser
        self.socket = socket.dup()
        
        self._len = parser.content_length
        if self._len and self._len < MAX_BODY:
            self.tmp = io.StringIO()
        else:
            self.tmp = tempfile.TemporaryFile()
        
        if len(buf) > 0:
            chunk, self.buf = parser.filter_body(buf)
            if chunk:
                self.tmp.write(chunk)
                self.tmp.seek(0)
            self._finalize()
    
    @property
    def len(self):
        if self._len:
            return self._len
        if self.socket:
            pos = self.tmp.tell()
            while True:
                if not self._tee(CHUNK_SIZE):
                    break
            self.tmp.seek(pos)
        self._len = self._tmp_size()
        return self._len
    
    def flush(self):
        self.tmp.flush()

    def read(self, length=-1):
        if not self.socket:
            ret = self.tmp.read(length)
            if isinstance(ret, bytes):
                ret = ret.decode()
            return ret
        
        if length < 0:
            r = self.tmp.read() or ''
            while True:
                chunk = self._tee(CHUNK_SIZE)
                if not chunk:
                    break
                r += chunk
        else:
            diff = self._tmp_size() - self.tmp.tell()
            if not diff:
                return self._ensure_length(self._tee(length), length)
            else:
                _length = min(diff, length)
                return self._ensuare_length(self.tmp.read(_length), _length)
    
    def readline(self, amt=-1):
        if not self.socket:
            return self.tmp.readline(amt)
        
        orig_size = self._tmp_size()
        if self.tmp.tell() == orig_size:
            if not self._tee(CHUNK_SIZE):
                return ''
            self.tmp.seek(orig_size)
        
        line = self.tmp.readline()
        if 0 < size and len(line) < size:
            self.tmp.seek(orig_size)
            while True:
                if not self._tee(CHUNK_SIZE):
                    self.tmp.seek(orig_size)
                    return self.tmp.readline(size)
        
        return line

    def readlines(self, sizehints=0):
        lines = []
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
            total += len(line)
            if 0 < sizehints <= total:
                break
        #end while
        return lines

    def next(self):
        r = self.readline()
        if not r:
            raise StopIteration()
        return r
    
    __next__ = next

    def __iter__(self):
        return self
    
    def _tee(self, length):
        while not self.parser.body_eof():
            data = read_partial(self.socket, length)
            self.buf += data.decode()
            chunk, self.buf = self.parser.filter_body(self.buf)
            if chunk:
                self.tmp.write(chunk.encode())
                self.tmp.seek(0, os.SEEK_END)
                return chunk
        self._finalize()
        return ''
    
    def _finalize(self):
        if self.parser.body_eof():
            if self.parser.is_chunked and self.socket:
                while not self.parser.trailing_header(self.buf):
                    data = read_partial(self.socket, CHUNK_SIZE)
                    if not data:
                        break
                    self.buf += data
            del self.buf # todo: why del
            self.socket = None

    def _tmp_size(self):
        if isinstance(self.tmp, io.StringIO):
            return len(self.tmp.getvalue()) # len(self.tmp)
        else:
            return int(os.fstat(self.tmp.fileno())[6])

    def _ensuare_length(self, buf, length):
        if not buf or not self._len:
            return buf
        
        while (len(buf) < length and self.len != self.tmp.pos()):
            buf += self._tee(length - len(buf))
        
        return buf
