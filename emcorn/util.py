import datetime

CHUNK_SIZE = 4096
MAX_BODY = 1024 * (80 + 32)

def import_app(modname):
    from demo.app import app
    return app

def http_date():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')