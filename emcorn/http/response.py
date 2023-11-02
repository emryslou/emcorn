import time

from emcorn.logging import log
from emcorn.util import http_date

class HttpResponse(object):
    def __init__(self, sock, data, req):
        self.socket = sock
        self.data = data
        self.req = req
        self.headers = self.req.response_headers or {}

        self.status = req.response_status
        self.SERVER_VERSION = req.SERVER_VERSION
    
    def write(self, data):
        self.socket.send(data)
    
    def send(self):
        res_headers = []
        res_headers.append('%s %s\r\n' % (self.req.parser.version, self.status))
        res_headers.append('%s %s\r\n' % ('Server:', self.SERVER_VERSION))
        res_headers.append('%s %s\r\n' % ('Date:', http_date()))
        res_headers.append('%s %s\r\n' % ('Status:', str(self.status)))
        res_headers.append('%s %s\r\n' % ('Connections:', 'close'))

        for name, value in self.headers.items():
            res_headers.append("%s: %s\r\n" % (name, value))
        
        header_body = "%s\r\n" % "".join(res_headers)
        self.write(header_body.encode())

        if self.req.parser.method == 'HEAD':
            return
        
        for chunk in self.data:
            self.write(chunk)
        
        self.req.close()
        if hasattr(self.data, 'close'):
            self.data.close()
