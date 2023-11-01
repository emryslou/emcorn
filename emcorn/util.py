import datetime

def import_app(modname):
    from demo.app import app
    return app

def http_date():
    return datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')