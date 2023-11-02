# -*- coding: utf-8 -
#
# This file is part of gunicorn released under the MIT license. 
# See the NOTICE for more information.

import t

@t.request("001.http")
def test_001(buf, p):
    headers = []
    i = p.filter_headers(headers, buf)
    t.ne(i, -1)
    
    t.eq(p.method, "PUT")
    t.eq(p.version, (1,0))
    t.eq(p.path, "/stuff/here")
    t.eq(p.query_string, "foo=bar")
    t.eq(sorted(p._headers), [
        ('Content-Length', '14'),
        ('Content-Type', 'application/json'),
        ('Server', 'http://127.0.0.1:5984')
    ])
    body, tr = p.filter_body(buf[i:])    
    t.eq(body, '{"nom": "nom"}')
    t.eq(p.body_eof(), True)

@t.request("002.http")
def test_002(buf, p):
    headers = []
    i = p.filter_headers(headers, buf)
    t.ne(i, -1)
       
    t.eq(p.method, "GET")
    t.eq(p.version, (1, 1))
    t.eq(p.path, "/test")
    t.eq(p.query_string, "")
    t.eq(sorted(p._headers), [
        ("Accept", "*/*"),
        ("Host", "0.0.0.0=5000"),
        ("User-Agent", "curl/7.18.0 (i486-pc-linux-gnu) libcurl/7.18.0 OpenSSL/0.9.8g zlib/1.2.3.3 libidn/1.1")
    ])
    body, tr = p.filter_body(buf[i:])
    t.eq(body, "")

@t.request("003.http")
def test_003(buf, p):
    headers = []
    i = p.filter_headers(headers, buf)
    t.ne(i, -1)
    t.eq(p.method, "GET")
    t.eq(p.version, (1, 1))
    t.eq(p.path, "/favicon.ico")
    t.eq(p.query_string, "")
    t.eq(sorted(p._headers), [
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("Accept-Charset", "ISO-8859-1,utf-8;q=0.7,*;q=0.7"),
        ("Accept-Encoding", "gzip,deflate"),
        ("Accept-Language", "en-us,en;q=0.5"),
        ("Connection", "keep-alive"),
        ("Host", "0.0.0.0=5000"),
        ("Keep-Alive", "300"),
        ("User-Agent", "Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9) Gecko/2008061015 Firefox/3.0"),
    ])
    body, tr = p.filter_body(buf[i:])
    t.eq(body, "")

@t.request("004.http")
def test_004(buf, p):
    headers = []
    i = p.filter_headers(headers, buf)
    t.ne(i, -1)
    t.eq(p.method, "GET")
    t.eq(p.version, (1, 1))
    t.eq(p.path, "/dumbfuck")
    t.eq(p.query_string, "")
    t.eq(p._headers, [("Aaaaaaaaaaaaa", "++++++++++")])
    body, tr = p.filter_body(buf[i:])
    t.eq(body, "")


@t.request("005.http")
def test_005(buf, p):
    headers = []
    i = p.filter_headers(headers, buf)
    t.ne(i, -1)
    t.eq(p.method, "GET")
    t.eq(p.version, (1, 1))
    t.eq(p.path, "/forums/1/topics/2375")
    t.eq(p.query_string, "page=1")
    
    
    t.eq(p.fragment, "posts-17408")
    body, tr = p.filter_body(buf[i:])
    t.eq(body, "")

@t.request("006.http")
def test_006(buf, p):
    headers = []
    i = p.filter_headers(headers, buf)
    t.ne(i, -1)
    t.eq(p.method, "GET")
    t.eq(p.version, (1, 1))
    t.eq(p.path, "/get_no_headers_no_body/world")
    t.eq(p.query_string, "")
    t.eq(p.fragment, "")
    body, tr = p.filter_body(buf[i:])
    t.eq(body, "")

@t.request("007.http")
def test_007(buf, p):
    headers = []
    i = p.filter_headers(headers, buf)
    t.ne(i, -1)
    t.eq(p.method, "GET")
    t.eq(p.version, (1, 1))
    t.eq(p.path, "/get_one_header_no_body")
    t.eq(p.query_string, "")
    t.eq(p.fragment, "")
    t.eq(p._headers, [('Accept', '*/*')])
    body, tr = p.filter_body(buf[i:])
    t.eq(body, "")
    
@t.request("008.http")
def test_008(buf, p):
    headers = []
    i = p.filter_headers(headers, buf)
    t.ne(i, -1)
    t.eq(p.method, "GET")
    t.eq(p.version, (1, 0))
    t.eq(p.path, "/get_funky_content_length_body_hello")
    t.eq(p.query_string, "")
    t.eq(p.fragment, "")
    t.eq(p._headers, [('Content-Length', '5')])
    body, tr = p.filter_body(buf[i:])
    t.eq(body, "HELLO")

@t.request("009.http")
def test_009(buf, p):
    headers = []
    i = p.filter_headers(headers, buf)
    t.ne(i, -1)
    t.eq(p.method, "POST")
    t.eq(p.version, (1, 1))
    t.eq(p.path, "/post_identity_body_world")
    t.eq(p.query_string, "q=search")
    t.eq(p.fragment, "hey")
    t.eq(sorted(p._headers), [
        ('Accept', '*/*'),
        ('Content-Length', '5'),
        ('Transfer-Encoding', 'identity')
    ])
    body, tr = p.filter_body(buf[i:])
    t.eq(body, "World")

@t.request("010.http")
def test_010(buf, p):
    headers = []
    i = p.filter_headers(headers, buf)
    t.ne(i, -1)
    t.eq(p.method, "POST")
    t.eq(p.version, (1, 1))
    t.eq(p.path, "/post_chunked_all_your_base")
    t.eq(p._headers, [('Transfer-Encoding', 'chunked')])
    t.eq(p.is_chunked, True)
    t.eq(p._chunk_eof, False)
    t.ne(p.body_eof(), True)
    body = ""
    buf = buf[i:]
    while not p.body_eof():
        chunk, buf = p.filter_body(buf)
        print(chunk)
        if chunk:
            body += chunk
    t.eq(body, "all your base are belong to us")
    
@t.request("011.http")
def test_011(buf, p):
    headers = []
    i = p.filter_headers(headers, buf)
    t.ne(i, -1)
    t.eq(p.method, "POST")
    t.eq(p.version, (1, 1))
    t.eq(p.path, "/two_chunks_mult_zero_end")
    t.eq(p._headers, [('Transfer-Encoding', 'chunked')])
    t.eq(p.is_chunked, True)
    t.eq(p._chunk_eof, False)
    t.ne(p.body_eof(), True)
    body = ""
    buf = buf[i:]
    while not p.body_eof():
        chunk, buf = p.filter_body(buf)
        if chunk:
            body += chunk
    t.eq(body, "hello world")
