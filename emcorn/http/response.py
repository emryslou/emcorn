
class HttpResponse(object):
    def __init__(self, req, data):
        self.req = req
        self.data = data
        self.headers = self.req.response_headers or {}
        self.fp = req.fp
    
    def write(self, data):
        self.fp.write(data)
    
    def send(self):
        if not self.data:
            return
        
        for chunk in self.data:
            self.write(chunk)
        
        self.fp.flush()
