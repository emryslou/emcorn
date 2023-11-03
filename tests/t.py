import sys
import os
project_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.append(project_dir)

import inspect
import re
import tempfile
import unittest

from emcorn.http import HttpParser, HttpRequest

dirname = os.path.dirname(__file__)

def data_source(fname):
    with open(fname) as handle:
        lines = []
        for line in handle:
            line = line.rstrip('\n').replace("\\r\\n", "\r\n")
            lines.append(line)
        
        return "".join(lines)

class request(object):
    def __init__(self, name):
        self.fname = os.path.join(dirname, 'requests', name)
    
    def __call__(self, func):
        def run():
            src = data_source(self.fname)
            func(src, HttpParser())
        
        run.__name__ = '%s(%s)' % (func.__name__, self.fname.split('/')[-1])

        return run

class FakeSocket(object):
    def __init__(self, data=""):
        self.tmp = tempfile.TemporaryFile()
        self.tmp.write(data)
        self.tmp.flush()
        self.tmp.seek(0)
    
    def fileno(self):
        return self.tmp.fileno()
    
    def len(self):
        return self.tmp.len # todo: need to checkout ????
    
    def recv(self, length=None):
        return self.tmp.read()
    
    def send(self, data):
        self.tmp.write(data)
        self.tmp.flush()
    
    def seek(self, offset, whence=0):
        self.tmp.seek(offset, whence)
    
    def dup(self):
        return self


class http_request(object):
    def __init__(self, name):
        self.fname = os.path.join(dirname, 'requests', name)
        self.fake_client, self.fake_server = ('127.0.0.1', 8120), ('127.0.0.1', 8089)

    def __call__(self, func):
        def inner():
            fsock = FakeSocket(data_source(self.fname).encode())
            req = HttpRequest(fsock, self.fake_client, self.fake_server)
            func(req)
        
        inner.__name__ = func.__name__
        return inner

def eq(a, b):
    assert a == b, "%r != %r" % (a, b)

def ne(a, b):
    assert a != b, "%r == %r" % (a, b)

def lt(a, b):
    assert a < b, "%r >= %r" % (a, b)

def gt(a, b):
    assert a > b, "%r <= %r" % (a, b)

def isin(a, b):
    assert a in b, "%r not in %r" % (a, b)

def isnotin(a, b):
    assert a not in b, "%r in %r" % (a, b)

def has(a, b):
    assert hasattr(a, b), "%r has not attribute %r" % (a, b)

def hasnot(a, b):
    assert not hasattr(a, b), "%r has an attribute %r" % (a, b)

def raises(exctype, func, *args, **kwargs):
    try:
        func(*args, **kwargs)
    except exctype as inst:
        pass
    else:
        func_name = getattr(func, 'func_name', '<builtin_function>')
        raise AssertionError('Function %d did not raise %s ' % (func_name, exctype.__name__))
