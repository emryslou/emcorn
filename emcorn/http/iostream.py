import errno
import socket

from emcorn.logging import log

class IOStream(object):
    chunk_size = 4096

    def __init__(self, sock):
        self.sock = sock
        self.sock.setblocking(False)
        self.buf = ''
    
    def recv(self, buffer_size):
        data = self.sock.recv(buffer_size)
        if not data:
            return ''
        return data
    
    def send(self, data):
        if isinstance(data, str):
            data = data.encode()
        return self.sock.send(data)
    
    def read_until(self, delimiter):
        while True:
            try:
                data = self.recv(self.chunk_size)
            except socket.error as e:
                return

            log.debug(f'recv from socket {data}')
            if isinstance(data, bytes):
                data = data.decode()
            self.buf = self.buf + data

            lb = len(self.buf)
            ld = len(delimiter)

            i = self.buf.find(delimiter)
            if i != -1:
                if i > 0:
                    r = self.buf[:i]
                self.buf = self.buf[i+ld:]
                return r