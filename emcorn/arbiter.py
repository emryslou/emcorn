import errno
import fcntl
import os
import select
import signal
import socket
import sys
import time

from emcorn.logging import log
from emcorn.worker import Worker



class Arbiter(object):

    __listener = None
    __workers = {}
    __pipe = []
    __sig_queue = []

    signals = map(
        lambda x: getattr(signal, 'SIG%s' % x),
        "WINCH CHLD QUIT INT TERM USR1 USR2 HUP TTIN TTOU".split()
    )
    signal_names = dict(
        (getattr(signal, name), name)
        for name in dir(signal)
        if name[:3] == 'SIG'
    )

    def __init__(self, address, worker_processes, modname):
        self.worker_processes = worker_processes
        self.address = address
        self.modname= modname

        self.alive = True
        self.pid = os.getpid()
        self.__init_signal()
        self.listen()

    def __init_signal(self):
        if self.__pipe:
            map(lambda p: p.close(), self.__pipe)
        self.__pipe = pair = os.pipe()
        map(self.set_non_blocking, pair)
        map(lambda p: fcntl.fcntl(p, fcntl.F_SETFD, fcntl.FD_CLOEXEC), pair)
        map(lambda s: signal.signal(s, self.sig_handle), self.signals)

    def listen(self):
        for i in range(5):
            try:
                self.__listener = self.init_socket()
                break
            except socket.error as err:
                if err.errno == errno.EADDRINUSE:
                    log.error('Connection in use : %s' % str(self.address))
                if i < 5:
                    log.error('Retrying in 1 second.')
                
                time.sleep(1)
        self.running = False
    
    def init_socket(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        sock.bind(self.address)
        
        sock.listen(2048)

        return sock

    def run(self):
        self.manage_workers()
        while self.alive:
            try:
                sig = self.__sig_queue.pop(0) if len(self.__sig_queue) else None
                if sig is None:
                    self.sleep()
                    self.alive = self.alive and sig not in (signal.SIGINT, signal.SIGQUIT)
                if self.alive:
                    self.reap_workers()
                    self.manage_workers()
            except Exception as exc:
                self.alive = False
            except KeyboardInterrupt:
                self.alive = False
        #end while self.alive
        
        log.info('main loop quit, stopping workers ...')
        self.kill_workers(signal.SIGINT)
    
    def manage_workers(self):
        if len(self.__workers.keys()) < self.worker_processes:
            self.spawn_workers()
        
        for pid, w in self.__workers.items():
            if w.id >= self.worker_processes:
                self.kill_worker(pid, signal.SIGQUIT)

    def spawn_workers(self):
        workers = set(w.id for w in self.__workers.values())
        for i in range(self.worker_processes):
            if i in workers:
                continue

            pid, worker = self.fork_worker(i)
            self.__workers[pid] = worker

            
    def fork_worker(self, worker_idx):
        worker = Worker(worker_idx, self.pid, self.__listener, self.modname)
        pid = os.fork()
        if pid != 0:
            return pid, worker
        
        try:
            log.info(f'worker {worker_idx} start ...')
            worker.run()
            sys.exit(0)
        except Exception as exc:
            import traceback
            log.warn(f'exception in worker process {exc}')
            traceback.print_stack(exc)
            sys.exit(-1)
        finally:
            log.debug('done')

    def kill_worker(self, pid, sig):
        worker = self.__workers.pop(pid)
        try:
            os.kill(pid, sig)
        finally:
            worker.close()

    def kill_workers(self, sig):
        for pid in self.__workers.keys():
            self.kill_worker(pid, sig)

    def sleep(self):
        try:
            ready = select.select([self.__pipe[0]], [], [], 3.0)
            if not ready[0]:
                return
            
            while os.read(self.__pipe[0], 1):
                pass
        except select.error as exc:
            if exc[0] not in [errno.EAGAIN, errno.EINTR]:
                raise
        except OSError as exc:
            if exc.errno not in [errno.EAGAIN, errno.EINTR]:
                raise
        

    def notify(self):
        try:
            os.write(self.PIPE[1], '.')
        except IOError as exc:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise
        
    def sig_handle(self, sig, frame):
        if len(self.__sig_queue) < 5:
            self.__sig_queue.append(sig)
        else:
            log.warn('warnning: ignore rapid singaling: %s' % sig)
        
        self.notify()
    

    def reap_workers(self):
        try:
            while True:
                wpid, status = os.waitpid(-1, os.WNOHANG)
                if not wpid:
                    break
                worker = self.__workers.pop(wpid)
                if not worker:
                    continue
                worker.close()
        except ChildProcessError:
            pass
        except OSError as exc:
            if exc.errno == errno.ECHILD:
                pass
            raise exc

    def set_non_blocking(self, fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)
    