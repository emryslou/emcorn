import sys

def app(environ, start_response):
    """Simplest possible application object"""
    data = ('Content From %s\n' % (sys._getframe().f_code.co_name)).encode()
    status = '200 OK'
    response_headers = [
        ('Content-type','text/plain'),
        ('Content-Length', str(len(data)))
    ]
    start_response(status, response_headers)
    return [data]


def error(environ, start_response):
    """Simplest possible application object"""
    data = ('Content From %s\n' % (sys._getframe().f_code.co_name)).encode()
    status = '200 OK'
    response_headers = [
        ('Content-type','text/plain'),
        ('Content-Length', str(len(data)))
    ]
    start_response(status, response_headers)
    raise RuntimeError('Error')
    return [data]

def application(environ, start_response):
    """Simplest possible application object"""
    data = ('Content From %s\n' % (sys._getframe().f_code.co_name)).encode()
    status = '200 OK'
    response_headers = [
        ('Content-type','text/plain'),
        ('Content-Length', str(len(data)))
    ]
    start_response(status, response_headers)
    return [data]