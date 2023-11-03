import t

from emcorn.http import tee

@t.http_request('001.http')
def test_001(req):
    e = req.read()
    print(e)