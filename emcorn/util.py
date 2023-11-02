import datetime
import errno
import select, socket
import time

CHUNK_SIZE = 4096
MAX_BODY = 1024 * (80 + 32)

def import_app(modname):
    from demo.app import app
    return app

def http_date():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')

def read_partial(sock, length):
    while True:
        try:
            ret = select.select([sock.fileno()], [], [], 2.0)
            if ret[0]:
                break
        except select.error as err:
            if err.errno == errno.EINTR:
                break
            raise err
    data = sock.recv(length)

    return data

def write(sock, data):
    buf = b''
    buf += data
    while True:
        try:
            _bytes = sock.send(buf)
            buf = buf[_bytes:]
            return _bytes
        except socket.error as err:
            if err.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                break
            elif err.errno in (errno.EPIPE,):
                continue
            raise

def write_nonblock(sock, data):
    while True:
        try:
            ret = select.select([], [sock.fileno()], [], 2.0)
            if ret[1]:
                break
        except socket.error as err:
            if err.errno == errno.EINTR:
                break
            raise err
    
    write(sock, data)

def close(sock):
    try:
        sock.shutdown(2)
    except socket.error:
        pass

    try:
        sock.close()
    except socket.error:
        pass
