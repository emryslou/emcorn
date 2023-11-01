import emcorn

class HttpResponse(object):
    def __init__(self, req, data):
        self.req = req
        self.data = data
        self.headers = self.req.response_headers or {}
        self.io = req.io
    
    def write(self, data):
        if isinstance(data, bytes):
            data = data.decode()
        self.io.send(data)
    
    def send(self):
        res_headers = []
        res_headers.append('%s %s\r\n' % (self.req.version, self.req.response_status))
        res_headers.append('%s %s\r\n' % ('Server:', self.req.SERVER_VERSION))
        res_headers.append('%s %s\r\n' % ('Date:', emcorn.util.http_date()))
        res_headers.append('%s %s\r\n' % ('Status:', str(self.req.response_status)))

        for name, value in self.req.response_headers.items():
            res_headers.append("%s: %s\r\n" % (name, value))
        
        header_body = "%s\r\n" % "".join(res_headers)
        self.io.send(header_body.encode())

        if self.req.method == 'HEAD':
            return
        
        for chunk in self.data:
            self.write(chunk)
        
        self.req.close()
        if hasattr(self.data, 'close'):
            self.data.close()
