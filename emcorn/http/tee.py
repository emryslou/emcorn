import ctypes
import io
import os
import tempfile

from emcorn.util import MAX_BODY, CHUNK_SIZE

class TeeInput(object):
    def __init__(self, socket, parser, buf, remain):
        self.buf = buf
        self.remain = remain
        self.parser = parser
        self.socket = socket
        
        self._len = parser.content_length
        if self._len and self._len < MAX_BODY:
            self.tmp = io.StringIO()
        else:
            self.tmp = tempfile.TemporaryFile()

        self.buf2 = ctypes.create_string_buffer(self.tmp)
        
        if len(buf) > 0:
            parser.fetch_body(self.buf2, buf)
            self._finalize()
            self.tmp.write(self.buf2)
            self.tmp.seek(0)
    
    @property
    def len(self):
        if self._len:
            return self._len
        if self.remain:
            pos = self.tmp.tell()
            while True:
                if not self._tee(self.remain, self.buf2):
                    break
            self.tmp.seek(pos)
        self._len = self._tmp_size()
        return self._len
    

    def read(self, length=None):
        if not self.remain:
            return self.tmp.read(length)
        
        if not length:
            r = self.tmp.read() # todo: or || ????
            while self._tee(self.remain, self.buf2):
                r += self.buf2.value
            return r
        else:
            r = self.buf2
            diff = self._tmp_size() - self.tmp.tell()
            if not diff:
                return self._ensure_length(self._tee(self.remain, r), self.remain)
            else:
                length = min(diff, self.remain)
                return self._ensuare_length(self._tee(length, r), length)
    
    def readline(self, amt=-1):
        pass

    def readlines(self, sizehints=0):
        pass

    def __next__(self):
        r = self.readline()
        if not r:
            raise StopIteration()
        return r
    
    next = __next__

    def __iter__(self):
        return self
    
    def _tee(self, length, dst):
        while not self.parser.body_eof() and self.remain:
            data = ctypes.create_string_buffer(length)
            length -= self.socket.recv_into(data, length)
            self.remain = length
            if self.parser.fetch_body(dst, data):
                self.tmp.write(dst)
                self.tmp.seek(0, os.SEEK_END)
                return dst
        self._finalize()
        return ''
    
    def _finalize(self):
        pass

    def _tmp_size(self):
        if isinstance(self.tmp, io.StringIO):
            return len(self.tmp.getvalue()) # len(self.tmp)
        else:
            return int(os.fstat(self.tmp.fileno()[6]))

    def _ensuare_length(self, buf, length):
        if not buf or not self._len:
            return buf
        
        while (len(buf) < length and self.len != self.tmp.pos()):
            buf += self._tee(length - len(buf), self.buf2)
        
        return buf
