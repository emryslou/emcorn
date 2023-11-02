import datetime
import errno
import select, socket

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
        except socket.error as err:
            if err.errno == errno.EINTR:
                break
            raise err
    data = sock.recv(length)

    return data

def write(sock, data):
    for i in range(2):
        try:
            return sock.send(data)
        except socket.error:
            if i >= 1:
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
    
    sock.send(data)
