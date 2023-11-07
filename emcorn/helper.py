import errno
import fcntl
import os
import sched, select, signal, socket
import time, threading, traceback

from exceptions import HttpParseError
from http.request import HttpRequest
from http.response import HttpResponse
from logger import logger as log

class Helper(object):
    def __init__(self, sock: socket.socket, app: callable):
        self.alive: bool = True
        self.alrm_interval: int = 1
        self.clients: dict = {}
        self.debug = False

        self.app = app
        self.sock: socket.socket = sock
        self.sock.setblocking(False)
        
        self.init_signal()

    def init_signal(self):
        signal.signal(signal.SIGALRM, self.signal_handle_alrm)
        signal.alarm(self.alrm_interval)

    def handle(self):
        while self.alive:
            while self.alive:
                try:
                    client, addr = self.sock.accept()
                    _request_time = time.time()
                    client.setblocking(0)
                    self.run_app(client, addr, _request_time)
                except OSError as oserr:
                    if oserr.errno in [errno.EAGAIN, errno.ECONNABORTED]:
                        break
                except KeyboardInterrupt:
                    self.alive = False
            
            while self.alive:
                read_fds = [self.sock.fileno()] + [client_fd for client_fd in self.clients.keys()]
                ready = select.select(read_fds, [], [], 1.0)
                if ready[0]:
                    for fd in ready[0]:
                        client_info = self.clients.get(fd, None)
                        if client_info is None:
                            continue
                        del client_info['ttl']
                        client_info['request_time'] = time.time()
                        client_info['client_reuse'] = True
                        client_info['client'].setblocking(0)
                        self.run_app(**client_info)
                    break
        log.info('helper handle loop quit ^_^.')

    def run_app(self, client, addr, request_time, client_reuse: bool = False):
        flags = fcntl.fcntl(client, fcntl.F_GETFD) | fcntl.FD_CLOEXEC
        fcntl.fcntl(client, fcntl.F_SETFL, flags)
        err_ = False
        request = None
        try:
            request = HttpRequest(client, request_time, addr, None)
            response = HttpResponse(request)
            wsgi_environ = request.environ()
            if request.keep_alive():
                response.response_headers['Keep-Alive'] = 'timeout=1, max=3'
            else:
                response.response_headers['Connection'] = 'close'
            
            if self.debug:
                response.response_headers['Connection-Reuse'] = 'True' if client_reuse else 'False'
            
            result = self.app(wsgi_environ, response.start_response)
            response(result)
        except HttpParseError as exc:
            if request:
                request.send(b'HTTP/1.0 400 Bad Request\r\n\r\n')
            else:
                client.send('HTTP/1.0 400 Bad Request\r\n\r\n')
            err_ = True
        except (BaseException) as exc:
            log.error(f'run app error: {exc}\nstack: {traceback.format_exc()}')
            err_ = True
        finally:
            client_ttl = 0
            if not err_ and request and request.keep_alive():
                client_ttl = 1

            client_info = self.clients.get(client.fileno(), None)
            if client_info is None:
                client_info = {
                    'ttl': client_ttl,
                    'client': client,
                    'addr': addr,
                    'request_time': request_time,
                }
            else:
                log.info('client reused')
                client_info.update({
                    'ttl': client_ttl,
                    'client': client,
                    'addr': addr,
                    'request_time': request_time
                })
            self.clients[client.fileno()] = client_info
            if client_ttl == 0:
                self.client_close()
            
    def client_close(self):
        # todo: sort
        _start = time.time()
        _max_handle_sec = 1
        while self.clients and time.time() < _start + _max_handle_sec:
            client_fd  = list(self.clients.keys())[0]
            client_info = self.clients[client_fd]
            # log.info(f'client_close {client_info}')
            if time.time() > client_info['ttl'] + client_info['request_time']:
                # log.info(f'client_close {client_info} closed')
                client_info['client'].close()
                self.clients.pop(client_fd)
    
    def quit(self):
        self.alive = False
    
    def signal_handle_alrm(self, sig, frame):
        signal.alarm(self.alrm_interval)
        self.client_close()
    
    def handle_timer(self):
        pass

    def close(self):
        signal.alarm(0)
        self.quit()
