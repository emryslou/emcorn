import datetime
import errno
import select, socket
import time

CHUNK_SIZE = 4096
MAX_BODY = 1024 * (80 + 32)

def import_app(modname):
    parts = modname.rsplit(':', 1)
    if len(parts) == 1:
        module, obj = modname, 'application'
    else:
        module, obj = parts[0], parts[1]
    
    
    mod = __import__(module)
    for p in module.split('.')[1:]:
        if not hasattr(mod, p):
            raise ImportError('Failed to import: %s' % modname)
        mod = getattr(mod, p)

    app = getattr(mod, obj)
    if not callable(app):
        raise TypeError('Application object must be callable.')

    return app

def http_date():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')

def read_partial(sock, length):
    while True:
        try:
            ret = select.select([sock.fileno()], [], [], 0)
            if ret[0]:
                break
        except select.error as err:
            if err.errno == errno.EINTR:
                continue
            raise err
    data = sock.recv(length)

    return data

def write(sock, data):
    buf = b''
    buf += data
    i = 0
    while True:
        try:
            _bytes = sock.send(buf)
            if _bytes < len(buf):
                buf = buf[_bytes:]
                continue
            return len(data)
        except socket.error as err:
            if err.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                break
            elif err.errno in (errno.EPIPE,):
                if i == 0:
                    continue
            raise
        i += 1

def write_lines(sock, lines_data):
    for line in list(lines_data):
        write(sock, line.encode())

def write_nonblock(sock, data):
    timeout = sock.gettimeout()
    if timeout != '0.0':
        sock.setblocking(False)
        ret = write(sock, data)
        sock.setblocking(True)
        return

    return write(sock, data)

def close(sock):
    try:
        sock.shutdown(2)
    except socket.error:
        pass

    try:
        sock.close()
    except socket.error:
        pass


def normalize_name(name):
    return '-'.join([w.lower().capitalize() for w in name.split('-')])