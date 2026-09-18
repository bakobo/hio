# -*- coding: utf-8 -*-
"""
Tests for http serving module
"""
import sys
import os
import time

import pytest

from hio import help
from hio.help import helping
from hio.base import tyming, doing
from hio.core import http
from hio.core.http import serving, httping


logger = help.ogler.getLogger()

tlsdirpath = os.path.dirname(
                os.path.dirname(
                        os.path.abspath(
                            sys.modules.get(__name__).__file__)))
certdirpath = os.path.join(tlsdirpath, 'tls', 'certs')

def test_bare_server_echo():
    """
    Test BaserServer service request response of echo non blocking
    """
    tymist = tyming.Tymist(tyme=0.0)

    with http.openServer(cls=http.BareServer, port = 6101, bufsize=131072, \
                         tymth=tymist.tymen()) as alpha:

        assert alpha.servant.ha == ('0.0.0.0', 6101)
        assert alpha.servant.eha == ('127.0.0.1', 6101)


        path = "http://{0}:{1}/".format('localhost', alpha.servant.eha[1])
        with http.openClient(bufsize=131072, path=path, tymth=tymist.tymen(), \
                             reconnectable=True,) as  beta:

            assert not beta.connector.accepted
            assert not beta.connector.connected
            assert not beta.connector.cutoff

            request = dict([('method', u'GET'),
                             ('path', u'/echo?name=fame'),
                             ('qargs', dict()),
                             ('fragment', u''),
                             ('headers', dict([('Accept', 'application/json'),
                                                ('Content-Length', 0)])),
                            ])

            beta.requests.append(request)

            while (beta.requests or beta.connector.txbs or not beta.responses or
                   not alpha.servant.ixes or not alpha.idle()):
                alpha.service()
                time.sleep(0.05)
                beta.service()
                time.sleep(0.05)

            assert beta.connector.accepted
            assert beta.connector.connected
            assert not beta.connector.cutoff

            assert len(alpha.servant.ixes) == 1
            assert len(alpha.stewards) == 1
            requestant = list(alpha.stewards.values())[0].requestant
            assert requestant.method == request['method']
            assert requestant.url == request['path']
            assert requestant.headers == help.Hict([('Host', 'localhost:6101'),
                                                         ('Accept-Encoding', 'identity'),
                                                         ('Accept', 'application/json'),
                                                         ('Content-Length', '0')])

            assert len(beta.responses) == 1
            response = beta.responses.popleft()
            assert response['data'] == {'version': 'HTTP/1.1',
                                        'method': 'GET',
                                        'path': '/echo',
                                        'qargs': {'name': 'fame'},
                                        'fragment': '',
                                        'headers': [['Host', 'localhost:6101'],
                                                    ['Accept-Encoding', 'identity'],
                                                    ['Accept', 'application/json'],
                                                    ['Content-Length', '0']],
                                        'body': '',
                                        'data': None}

            responder = list(alpha.stewards.values())[0].responder
            assert responder.status == response['status']
            assert responder.headers == response['headers']


def test_wsgi_server():
    """
    Test WSGI Server service request response
    """
    tymist = tyming.Tymist(tyme=0.0)

    def wsgiApp(environ, start_response):
        start_response('200 OK', [('Content-type','text/plain'),
                                  ('Content-length', '12')])
        return [b"Hello World!"]

    with http.openServer(port = 6101, bufsize=131072, app=wsgiApp, \
                         tymth=tymist.tymen()) as alpha:  # passthrough

        assert alpha.servant.ha == ('0.0.0.0', 6101)
        assert alpha.servant.eha == ('127.0.0.1', 6101)

        path = "http://{0}:{1}/".format('localhost', alpha.servant.eha[1])

        with http.openClient(bufsize=131072, path=path, reconnectable=True, \
                             tymth=tymist.tymen()) as beta:

            assert not beta.connector.accepted
            assert not beta.connector.connected
            assert not beta.connector.cutoff

            request = dict([('method', u'GET'),
                             ('path', u'/echo?name=fame'),
                             ('qargs', dict()),
                             ('fragment', u''),
                             ('headers', dict([('Accept', 'application/json'),
                                                ('Content-Length', 0)])),
                            ])

            beta.requests.append(request)

            while (beta.requests or beta.connector.txbs or not beta.responses or
                   not alpha.idle()):
                alpha.service()
                time.sleep(0.05)
                beta.service()
                time.sleep(0.05)

            assert beta.connector.accepted
            assert beta.connector.connected
            assert not beta.connector.cutoff

            assert len(alpha.servant.ixes) == 1
            assert len(alpha.reqs) == 1
            assert len(alpha.reps) == 1
            requestant = list(alpha.reqs.values())[0]
            assert requestant.method == request['method']
            assert requestant.url == request['path']
            assert requestant.headers == help.Hict([('Host', 'localhost:6101'),
                                                         ('Accept-Encoding', 'identity'),
                                                         ('Accept', 'application/json'),
                                                         ('Content-Length', '0')])


            assert len(beta.responses) == 1
            response = beta.responses.popleft()
            assert response['body'] == (b'Hello World!')
            assert response['status'] == 200

            responder = list(alpha.reps.values())[0]
            assert responder.status.startswith(str(response['status']))
            assert responder.headers == response['headers']


def test_wsgi_server_tls():
    """
    Test Valet WSGI service with secure TLS request response
    """
    tymist = tyming.Tymist(tyme=0.0)

    def wsgiApp(environ, start_response):
        start_response('200 OK', [('Content-type','text/plain'),
                                  ('Content-length', '12')])
        return [b"Hello World!"]

    serverCertCommonName = 'localhost' # match hostname uses servers's cert commonname
    #serverKeypath = '/etc/pki/tls/certs/server_key.pem'  # local server private key
    #serverCertpath = '/etc/pki/tls/certs/server_cert.pem'  # local server public cert
    #clientCafilepath = '/etc/pki/tls/certs/client.pem' # remote client public cert

    serverKeypath = certdirpath + '/server_key.pem'  # local server private key
    serverCertpath = certdirpath + '/server_cert.pem'  # local server public cert
    clientCafilepath = certdirpath + '/client.pem' # remote client public cert

    with http.openServer(port = 6101, bufsize=131072, app=wsgiApp, \
                         scheme='https', keypath=serverKeypath, \
                         certpath=serverCertpath, cafilepath=clientCafilepath, \
                         tymth=tymist.tymen()) as alpha:

        assert alpha.servant.ha == ('0.0.0.0', 6101)
        assert alpha.servant.eha == ('127.0.0.1', 6101)

        #clientKeypath = '/etc/pki/tls/certs/client_key.pem'  # local client private key
        #clientCertpath = '/etc/pki/tls/certs/client_cert.pem'  # local client public cert
        #serverCafilepath = '/etc/pki/tls/certs/server.pem' # remote server public cert

        clientKeypath = certdirpath + '/client_key.pem'  # local client private key
        clientCertpath = certdirpath + '/client_cert.pem'  # local client public cert
        serverCafilepath = certdirpath + '/server.pem' # remote server public cert

        path = "https://{0}:{1}/".format('localhost', alpha.servant.eha[1])

        with http.openClient(bufsize=131072, path=path, scheme='https', \
                    certedhost=serverCertCommonName, keypath=clientKeypath, \
                    certpath=clientCertpath, cafilepath=serverCafilepath, \
                    tymth=tymist.tymen(), reconnectable=True,) as beta:

            assert not beta.connector.accepted
            assert not beta.connector.connected
            assert not beta.connector.cutoff

            request = dict([('method', u'GET'),
                             ('path', u'/echo?name=fame'),
                             ('qargs', dict()),
                             ('fragment', u''),
                             ('headers', dict([('Accept', 'application/json'),
                                                ('Content-Length', 0)])),
                            ])

            beta.requests.append(request)

            while (beta.requests or beta.connector.txbs or not beta.responses or
                   not alpha.idle()):
                alpha.service()
                time.sleep(0.05)
                beta.service()
                time.sleep(0.05)

            assert beta.connector.accepted
            assert beta.connector.connected
            assert not beta.connector.cutoff

            assert len(alpha.servant.ixes) == 1
            assert len(alpha.reqs) == 1
            assert len(alpha.reps) == 1
            requestant = list(alpha.reqs.values())[0]
            assert requestant.method == request['method']
            assert requestant.url == request['path']
            assert requestant.headers == help.Hict([('Host', 'localhost:6101'),
                                                         ('Accept-Encoding', 'identity'),
                                                         ('Accept', 'application/json'),
                                                         ('Content-Length', '0')])

            assert len(beta.responses) == 1
            response = beta.responses.popleft()
            assert response['body'] == (b'Hello World!')
            assert response['status'] == 200

            responder = list(alpha.reps.values())[0]
            responder.status.startswith(str(response['status']))
            assert responder.headers == response['headers']


def test_server_client_doers():
    """
    Test HTTP ServerDoer ClientDoer classes
    """
    tock = 0.03125
    ticks = 16
    limit = ticks * tock
    doist = doing.Doist(tock=tock, real=True, limit=limit)
    assert doist.tyme == 0.0  # on next cycle
    assert doist.tock == tock == 0.03125
    assert doist.real == True
    assert doist.limit == limit == 0.5
    assert doist.doers == []

    def wsgiApp(environ, start_response):
        start_response('200 OK', [('Content-type','text/plain'),
                              ('Content-length', '12')])
        return [b"Hello World!"]

    port = 6101
    server = http.Server(port=port, app=wsgiApp, tymth=doist.tymen())
    assert server.servant.tyme == doist.tyme

    serdoer = http.ServerDoer(tymth=doist.tymen(), server=server)
    assert serdoer.server ==  server
    assert serdoer.tyme ==  serdoer.server.servant.tyme == doist.tyme

    path = "http://{0}:{1}/".format('localhost', port)
    client = http.Client(path=path, tymth=doist.tymen())
    assert client.connector.tyme == doist.tyme

    request = dict([('method', u'GET'),
                     ('path', u'/echo?name=fame'),
                     ('qargs', dict()),
                     ('fragment', u''),
                     ('headers', dict([('Accept', 'application/json'),
                                        ('Content-Length', 0)])),
                    ])

    client.requests.append(request)

    clidoer = http.ClientDoer(tymth=doist.tymen(), client=client)
    assert clidoer.client == client
    assert clidoer.tyme == clidoer.client.connector.tyme == doist.tyme

    assert serdoer.tock == 0.0  # ASAP
    assert clidoer.tock == 0.0  # ASAP

    doers = [serdoer, clidoer]

    doist.do(doers=doers, limit=limit)
    assert doist.tyme == limit
    assert server.servant.opened == False
    assert client.connector.opened == False

    assert len(client.responses) == 1
    response = client.responses.popleft()
    assert response['body'] == (b'Hello World!')
    assert response['status'] == 200
    """End Test """


def test_requestant_max_body_known_length():
    """
    Test Requestant.parseBody rejects a known content-length body that exceeds
    the configured maximum size, instead of buffering it all into
    memory. Drives parseBody directly with a crafted oversized msg.
    """
    maxBody = 100
    oversized = bytearray(b'x' * (maxBody + 1))  # 101 bytes, over the limit

    req = serving.Requestant(msg=bytearray(oversized))
    req.maxBody = maxBody  # per-instance cap (ignored by unfixed code)
    req.chunked = False
    req.length = len(oversized)  # declared content-length exceeds maxBody
    req.headed = True

    with pytest.raises(httping.HTTPException) as exc:
        for _ in req.parseBody():
            pass

    assert exc.value.status == 413  # Request Entity Too Large
    # memory bounded: an over-limit declared length is rejected before buffering
    assert len(req.body) <= maxBody
    assert not req.bodied  # never completed parsing the oversized body
    """End Test"""


def test_requestant_max_body_chunked():
    """
    Test Requestant.parseBody bounds memory on a chunked body whose accumulated
    chunks exceed the configured maximum size, even though chunked transfer has
    no declared content-length. Stops and raises 413 during accumulation.
    """
    maxBody = 100
    chunkData = b'a' * 50
    chunkHex = format(len(chunkData), 'x').encode('ascii')  # b'32'
    oneChunk = chunkHex + b'\r\n' + chunkData + b'\r\n'
    # three 50-byte chunks (150 bytes total) then the terminating empty chunk
    msg = bytearray(oneChunk * 3 + b'0\r\n\r\n')

    req = serving.Requestant(msg=msg)
    req.maxBody = maxBody
    req.chunked = True
    req.length = None
    req.headed = True

    with pytest.raises(httping.HTTPException) as exc:
        for _ in req.parseBody():
            pass

    assert exc.value.status == 413
    # memory bounded: accumulation stopped at/below the cap, not the full 150
    assert len(req.body) <= maxBody
    assert not req.bodied
    """End Test"""


def test_requestant_body_under_max_body():
    """
    Test Requestant.parseBody parses a body under the limit identically to
    legacy behavior (pure addition: under-limit requests are unaffected).
    """
    body = b'hello world'
    req = serving.Requestant(msg=bytearray(body), maxBody=100)
    req.chunked = False
    req.length = len(body)
    req.headed = True

    for _ in req.parseBody():
        pass

    assert req.body == body
    assert req.bodied
    assert req.length == len(body)
    """End Test"""


def test_requestant_max_body_config():
    """
    Test the MaxBody knob: sane generous default, configurable per instance,
    and 0/None means unlimited (opt out to preserve legacy unbounded behavior).
    """
    # default: class attribute, at least a few MiB, and used when not overridden
    assert serving.Requestant.MaxBody >= 1024 * 1024  # generous default (>= 1 MiB)
    req = serving.Requestant()
    assert req.maxBody == serving.Requestant.MaxBody

    data = b'x' * 500

    # a small cap rejects an over-limit body
    req = serving.Requestant(msg=bytearray(data), maxBody=100)
    req.chunked = False
    req.length = len(data)
    req.headed = True
    with pytest.raises(httping.HTTPException) as exc:
        for _ in req.parseBody():
            pass
    assert exc.value.status == 413

    # maxBody == 0 disables the cap (unlimited) so the same body parses
    req = serving.Requestant(msg=bytearray(data), maxBody=0)
    req.chunked = False
    req.length = len(data)
    req.headed = True
    for _ in req.parseBody():
        pass
    assert req.body == data
    assert req.bodied
    """End Test"""


def test_max_body_server_plumbing():
    """
    Test the maxBody knob is accepted and stored by the WSGI Server and the
    BareServer, and is passed through Steward to its Requestant.
    """
    def app(environ, start_response):  # minimal wsgi app
        start_response("200 OK", [])
        return [b""]

    server = serving.Server(app=app, port=8080, maxBody=12345)
    assert server.maxBody == 12345
    server.servant.close()

    bare = serving.BareServer(port=8081, maxBody=6789)
    assert bare.maxBody == 6789
    bare.servant.close()

    # Steward forwards maxBody to the Requestant it creates
    class FakeRemoter:
        def __init__(self):
            self.rxbs = bytearray()
    steward = serving.Steward(remoter=FakeRemoter(), maxBody=222)
    assert steward.requestant.maxBody == 222
    """End Test"""


if __name__ == '__main__':
    test_server_client_doers()
    test_requestant_max_body_known_length()
    test_requestant_max_body_chunked()
    test_requestant_body_under_max_body()
    test_requestant_max_body_config()
    test_max_body_server_plumbing()
