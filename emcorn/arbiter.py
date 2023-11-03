import errno
import fcntl
import os
import select, signal, socket, sys
import threading, time


from emcorn.logging import log
from emcorn.worker import Worker



class Arbiter(object):

    __listener = None
    __workers = {}
    __pipe = []
    __sig_queue = []

    signals = map(
        lambda x: getattr(signal, 'SIG%s' % x),
        "CHLD HUP QUIT INT TERM TTIN TTOU USR1 USR2 WINCH".split()
    )
    signal_names = dict(
        (getattr(signal, name), name[3:].lower())
        for name in dir(signal)
        if name[:3] == 'SIG' and name[3] != '_'
    )

    def __init__(self, address, worker_processes, app, debug=False):
        self.worker_processes = worker_processes
        self.address = address
        self.app= app
        self.debug = debug
        self.timeout = 30
        self.reexec_pid = 0

        self.alive = True
        self.pid = os.getpid()
        self.init_signal()
        self.listen()
        log.info('Booted Arbiter: %s' % self.pid)

    def init_signal(self):
        if self.__pipe:
            [p.close() for p in self.__pipe]
        self.__pipe = pair = os.pipe()

        [self.set_non_blocking(p) for p in pair]
        [fcntl.fcntl(p, fcntl.F_SETFD, fcntl.FD_CLOEXEC) for p in pair]
        [signal.signal(s, self.sig_handle) for s in self.signals]

    def listen(self):
        if 'EMCORN_FD' in os.environ:
            fd = int(os.environ['EMCORN_FD'])
            del os.environ['EMCORN_FD']
            try:
                self.__listener = self.init_socket(fd)
                return
            except socket.error as err:
                if err.errno == errno.EADDRINUSE:
                    log.error('Connection in use : %s' % str(self.address))
                else:
                    raise

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
    
    def init_socket(self, fd = None):
        if fd is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_opt(sock)
            sock.bind(self.address)
            sock.listen(2048)
        else:
            sock = socket.fromfd(fd, socket.AF_INET, socket.SOCK_STREAM)
            self.socket_opt(sock)

        return sock
    
    def socket_opt(self, sock):
        sock.setblocking(False)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 0)
        if hasattr(socket, 'TCP_CORK'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_CORK, 1)
        elif hasattr(socket, 'TCP_NOPUSG'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NOPUSG, 1)


    def run(self):
        self.manage_workers()
        max_raise_exc_retry = 10
        while self.alive:
            try:
                self.reap_workers()
                sig = self.__sig_queue.pop(0) if len(self.__sig_queue) else None
                if sig is None:
                    self.sleep()
                    self.murder_workers()
                    if self.alive:
                        self.manage_workers()
                    continue
                
                if sig not in self.signal_names:
                    log.info('Ignoring unknown signal: %s' % sig)
                    continue
                signame = self.signal_names.get(sig)
                sig_handler = getattr(self, 'sig_handler_%s' % signame, None)
                if not sig_handler:
                    log.error('Unhandled signal: %s' % signame)
                    continue
                sig_handler()
                self.wakeup()
            except Exception as exc:
                import traceback
                traceback.print_exc(file=sys.stdout)
                if max_raise_exc_retry < 0:
                    self.alive = False
                else:
                    max_raise_exc_retry -= 1
            except KeyboardInterrupt:
                self.alive = False
            except StopIteration:
                break
        #end while self.alive
        self.stop()
        sys.exit(0)
    
    def stop(self, graceful = True):
        self.__listener = None
        sig = signal.SIGQUIT
        if not graceful:
            sig = signal.SIGTERM
        
        limit = time.time() + self.timeout
        while len(self.__workers) and time.time() < limit:
            self.kill_workers(sig)
            time.sleep(0.1)
            self.reap_workers()
        
        self.kill_workers(signal.SIGKILL)

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
        worker = Worker(worker_idx, self.pid, self.__listener, self.app, self.timeout / 2, self.debug)
        pid = os.fork()
        if pid != 0:
            return pid, worker
        
        try:
            log.info(f'worker {worker_idx} start ...')
            worker.run()
            sys.exit(0)
        except Exception as exc:
            import traceback
            log.error(f'exception in worker process {exc}')
            traceback.print_exc(file=sys.stderr)
            sys.exit(-1)
        finally:
            log.debug('worker exit ....')

    def kill_worker(self, pid, sig):
        worker = self.__workers.get(pid, None)
        try:
            os.kill(pid, sig)
        finally:
            if worker: worker.close()

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
        except (BlockingIOError, OSError) as exc:
            if exc.errno not in [errno.EAGAIN, errno.EINTR]:
                raise
        except KeyboardInterrupt:
            self.alive = False
    
    def murder_workers(self):
        for pid, worker in self.__workers.items():
            try:
                diff = time.time() - os.fstat(worker.tmp.fileno()).st_mtime
            except:
                diff = 0
            
            if diff < self.timeout:
                continue
            log.info(f'{pid} timeout: {diff} >= {self.timeout}, killed')
            self.kill_worker(pid, signal.SIGKILL)

    def wakeup(self):
        try:
            os.write(self.__pipe[1], b'.')
        except IOError as exc:
            if exc.errno not in [errno.EAGAIN, errno.EINTR]:
                raise
        
    def sig_handle(self, sig, frame):
        if len(self.__sig_queue) < 5:
            self.__sig_queue.append(sig)
            self.wakeup()
        else:
            log.warn('warnning: ignore rapid singaling: %s' % sig)
    
    def sig_handler_quit(self):
        raise StopIteration()
    
    def sig_handler_int(self):
        self.alive = False
        self.stop(False)
        raise StopIteration()
    
    def sig_handler_term(self):
        self.alive = False
        self.stop(False)
        raise StopIteration()
    
    def sig_handler_ttin(self):
        self.worker_processes += 1
    
    def sig_handler_ttou(self):
        if self.worker_processes > 0:
            self.worker_processes -= 1
    
    def sig_handler_chld(self):
        self.wakeup()
    
    def sig_handler_hup(self):
        self.reexec()
        raise StopIteration()
    
    def sig_handler_usr1(self):
        self.kill_workers(signal.SIGUSR1)
    
    def sig_handler_usr2(self):
        self.reexec()
    
    def sig_handler_winch(self):
        if os.getppid() == 1 or os.getpgrp() != os.getpid():
            log.info('graceful stop of workers')
            self.stop()
        else:
            log.info('SIGWINCH ignored. not daemonized')
    

    def reexec(self):
        self.reexec_pid = os.fork()
        if self.reexec_pid == 0:
            os.environ['EMCORN_FD'] = str(self.__listener.fileno())
            self.__listener.setblocking(True)
            os.execlp(*(sys.argv[0],) + tuple(sys.argv))

    def reap_workers(self):
        try:
            while True:
                wpid, status = os.waitpid(-1, os.WNOHANG)
                if not wpid:
                    break
                if self.reexec_pid == wpid:
                    self.reexec_pid = 0
                else:
                    worker = self.__workers.pop(wpid)
                    if not worker:
                        continue
                    worker.close()
                
        except ChildProcessError:
            return
        except OSError as exc:
            if exc.errno == errno.ECHILD:
                pass
            raise exc

    def set_non_blocking(self, fd):
        flags = fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK
        fcntl.fcntl(fd, fcntl.F_SETFL, flags)
    