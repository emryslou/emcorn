from logger import logger as log
class HttpResponse(object):
    def __init__(self, request):
        self.request = request
        self.response_status = 400
        self.response_status_hint = 'Bad Request'
        self.response_headers = {}
        self.response_body = None
        self.sended_headers = False

    def __call__(self, body):
        self.response_body = body
        self.send_status()
        self.send_headers()
        self.send_body()
        self.send_finish()
    
    def start_response(self, http_status: str, headers: list):
        status, status_hint = http_status.split(' ', 2)
        self.response_status = status
        self.response_status_hint = status_hint

        for header_name, header_value in headers:
            self.response_headers[header_name] = header_value
    
    def send_status(self):
        status = (
            f'HTTP/1.1 {self.response_status} {self.response_status_hint}'
            '\r\n'
        )
        self.request.send(status.encode())
    
    def send_headers(self):
        for header_name, header_value in self.response_headers.items():
            header = f'{header_name}: {header_value}\r\n'
            self.request.send(header.encode())
        self.request.send(b'\r\n')
        self.sended_headers = True
    
    def send_body(self):
        if self.response_body:
            for chunk in self.response_body:
                self.request.send(chunk)
    
    def send_finish(self):
        self.request.send(b'\r\n\r\n')
