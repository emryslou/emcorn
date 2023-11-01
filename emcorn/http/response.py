
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
        if not self.data:
            return
        
        for chunk in self.data:
            self.write(chunk)
