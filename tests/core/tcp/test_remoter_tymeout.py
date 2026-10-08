# -*- encoding: utf-8 -*-
"""
tests.core.tcp.test_remoter_tymeout

Server and ServerTls built each accepted Remoter with ``timeout=self.tymeout``
but Remoter's parameter is ``tymeout``. The keyword fell into **kwa and was
dropped, so every accepted connection got Remoter.Tymeout (0.0) and never
timed out, whatever tymeout the server was given. In particular http.Server's
idle-connection tymeout (5 s by default) never applied, so a client could hold
a connection open indefinitely by never finishing its request headers.
"""
import socket
import time

from hio.base import tyming
from hio.core import tcp, http


def _accept(server, port):
    sock = socket.create_connection(("127.0.0.1", port))
    for _ in range(50):
        server.serviceConnects()
        if server.ixes:
            break
        time.sleep(0.02)
    assert server.ixes
    return sock, next(iter(server.ixes.values()))


def test_accepted_remoter_gets_server_tymeout():
    tymist = tyming.Tymist()
    with tcp.openServer(tymth=tymist.tymen(), ha=("", 6103), tymeout=1.5) as server:
        sock, ix = _accept(server, 6103)
        try:
            assert ix.tymeout == 1.5
            assert ix.tymer.duration == 1.5
        finally:
            sock.close()


def test_accepted_remoter_default_never_times_out():
    tymist = tyming.Tymist()
    with tcp.openServer(tymth=tymist.tymen(), ha=("", 6104)) as server:
        sock, ix = _accept(server, 6104)
        try:
            assert ix.tymeout == 0.0
        finally:
            sock.close()


def test_http_server_drops_connection_with_unfinished_headers():
    """A client that never finishes its headers is dropped after tymeout."""
    def wsgiApp(environ, start_response):
        start_response("200 OK", [("Content-Length", "2")])
        return [b"ok"]

    tymist = tyming.Tymist(tock=0.25)
    port = 6105
    server = http.Server(port=port, app=wsgiApp, tymth=tymist.tymen(), tymeout=1.0)
    server.servant.reopen()
    sock = socket.create_connection(("127.0.0.1", port))
    try:
        sock.sendall(b"GET / HTTP/1.1\r\nHost: loc")  # headers never finish
        for _ in range(20):
            server.service()
            if server.servant.ixes:
                break
            time.sleep(0.02)
        assert server.servant.ixes  # accepted and held

        for _ in range(8):  # two virtual seconds with no further bytes
            tymist.tick()
            server.service()
        assert not server.servant.ixes  # dropped once idle past tymeout
    finally:
        sock.close()
        server.servant.close()
