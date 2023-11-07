
import errno
import os
import select, signal, socket, sys
import traceback, time

from helper import Helper
from logger import logger as log

class NoBody(object):
    def __init__(self, **opts):
        self.alive = True

        self.processes = int(opts.pop('processes', 1))
        self.address = (opts.pop('host', '127.0.0.1'), int(opts.pop('port', 8089)))
        self.backlog = int(opts.pop('backlog', 1024))
        self.app = opts.pop('app', None)
        assert self.app is not None
        if opts:
            raise RuntimeError(f'Too many opts {opts}')

        self.helpers = {}
        self.sock: socket.socket
        self.init_socket()
    
    def run(self):
        while self.alive:
            try:
                log.debug('main loop running')
                self.monitor_helpers()
                self.manage_helpers()
            except KeyboardInterrupt:
                self.alive = False
        
        log.info('master process quit ...')
        self.quit()

    def quit(self):
        for helper in self.helpers.values():
            helper.close()
        self.sock.close()
        self.sock = None

    def init_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
        if hasattr(socket, 'TCP_CORK'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_CORK, 1)
        elif hasattr(socket, 'TCP_NOPUSG'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NOPUSG, 1)
        self.sock.bind(self.address)
        self.sock.listen(self.backlog)

    def manage_helpers(self):
        fork_procs = self.processes - len(self.helpers.keys())
        for _ in range(fork_procs):
            pid, helper = self.spawn_worker()
            self.helpers[pid] = helper
    
    def monitor_helpers(self):
        while self.alive and len(self.helpers):
            try:
                pid, status = os.waitpid(-1, 0)
                if pid == 0:
                    continue
                helper = self.helpers.pop(pid, None)
                if not helper:
                    continue
                status = os.WEXITSTATUS(status)
                log.debug(f'helper {pid} exit, status: {status}')
                helper.close()
            except ChildProcessError as cperr:
                break

    def spawn_worker(self):
        helper = Helper(self.sock, self.app)
        pid = os.fork()
        if pid != 0:
            return pid, helper
        
        # helper processor
        log.debug(f'helper started {os.getpid()}')
        try:
            helper.handle()
            log.debug('helper quit normal')
            os._exit(0)
        except KeyboardInterrupt:
            log.debug('helper quit cause ctrl + c')
            helper.close()
            os._exit(1)
        except (BaseException, OSError) as exc:
            log.error(f'helper exit unexpectedly, error: {exc}, \nstack: {traceback.format_exc()}')
            os._exit(127)
