class Worker(object):
    def __init__(self, nr, tmp):
        self.nr = nr
        self.tmp = tmp

class HttpServer(object):
    
    def __init__(
        self, app, worker_processes, timeout=60, init_listeners = [],
        pidfile=None, logging_handler = None, **opts
    ):
        pass