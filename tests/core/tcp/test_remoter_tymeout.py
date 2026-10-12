# -*- encoding: utf-8 -*-
"""
tests.core.tcp.test_remoter_tymeout

Server and ServerTls built each accepted Remoter with ``timeout=self.tymeout``
but Remoter's parameter is ``tymeout``. The keyword fell into **kwa and was
dropped, so every accepted connection got Remoter.Tymeout (0.0) and never
timed out, whatever tymeout the server was given. In particular http.Server's
idle-connection tymeout (5 s by default) never applied, so a client could hold
a connection open indefinitely by never finishing its request headers.

The remaining tests cover what turning that tymeout on exposed: the tymeout
must measure idle tyme from the latest byte, must not cut a response in
progress, must not crash a server serviced without a Tymist, and must also
reach TLS connections that never finish their handshake.

Ports 6431-6440 are used only here.
"""
import os
import socket
import time

import pytest

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


def _serviceUntil(server, predicate, tries=100):
    """Service server in real time until predicate() or give up."""
    for _ in range(tries):
        server.service()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _recvAll(sock, server, until, tries=100):
    """Service server and collect bytes from sock until `until` is in them."""
    sock.setblocking(False)
    data = b""
    for _ in range(tries):
        server.service()
        try:
            chunk = sock.recv(4096)
        except BlockingIOError:
            chunk = b""
        data += chunk
        if until in data:
            break
        time.sleep(0.01)
    return data


def _okApp(environ, start_response):
    start_response("200 OK", [("Content-Length", "2")])
    return [b"ok"]


def test_accepted_remoter_gets_server_tymeout():
    tymist = tyming.Tymist()
    with tcp.openServer(tymth=tymist.tymen(), ha=("", 6431), tymeout=1.5) as server:
        sock, ix = _accept(server, 6431)
        try:
            assert ix.tymeout == 1.5
            assert ix.tymer.duration == 1.5
        finally:
            sock.close()


def test_accepted_remoter_default_never_times_out():
    tymist = tyming.Tymist()
    with tcp.openServer(tymth=tymist.tymen(), ha=("", 6432)) as server:
        sock, ix = _accept(server, 6432)
        try:
            assert ix.tymeout == 0.0
        finally:
            sock.close()


def test_http_server_drops_connection_with_unfinished_headers():
    """A client that never finishes its headers is dropped after tymeout."""
    tymist = tyming.Tymist(tock=0.25)
    port = 6433
    server = http.Server(port=port, app=_okApp, tymth=tymist.tymen(), tymeout=1.0)
    server.servant.reopen()
    sock = socket.create_connection(("127.0.0.1", port))
    try:
        sock.sendall(b"GET / HTTP/1.1\r\nHost: loc")  # headers never finish
        assert _serviceUntil(server, lambda: server.servant.ixes)  # accepted and held

        for _ in range(8):  # two virtual seconds with no further bytes
            tymist.tick()
            server.service()
        assert not server.servant.ixes  # dropped once idle past tymeout
    finally:
        sock.close()
        server.servant.close()


def test_http_server_tymeout_counts_from_last_byte():
    """
    A client trickling one byte per tick is kept while bytes arrive faster
    than tymeout, and dropped once tymeout has passed since the LAST byte.
    A lossless tymer restart per byte would instead bank a whole tymeout per
    byte, and the trickler would never be dropped.
    """
    tymist = tyming.Tymist(tock=0.25)
    port = 6434
    server = http.Server(port=port, app=_okApp, tymth=tymist.tymen(), tymeout=1.0)
    server.servant.reopen()
    sock = socket.create_connection(("127.0.0.1", port))
    try:
        sock.sendall(b"G")  # request line that never ends
        assert _serviceUntil(server, lambda: server.servant.ixes)
        ix = next(iter(server.servant.ixes.values()))

        for _ in range(20):  # five virtual seconds, one byte per 0.25 s
            tymist.tick()
            before = len(ix.rxbs)
            sock.sendall(b"E")
            assert _serviceUntil(server, lambda: len(ix.rxbs) > before)
            assert server.servant.ixes  # still held while bytes keep coming

        for _ in range(3):  # 0.75 s since the last byte
            tymist.tick()
            server.service()
        assert server.servant.ixes

        for _ in range(2):  # 1.25 s since the last byte
            tymist.tick()
            server.service()
        assert not server.servant.ixes
    finally:
        sock.close()
        server.servant.close()


def test_bare_server_drops_idle_connection():
    """BareServer removes an expired connection without mutating ixes mid-iteration."""
    tymist = tyming.Tymist(tock=0.25)
    port = 6435
    server = http.BareServer(port=port, tymth=tymist.tymen(), timeout=1.0)
    server.servant.reopen()
    sock = socket.create_connection(("127.0.0.1", port))
    try:
        sock.sendall(b"GET / HTTP/1.1\r\nHost: loc")  # headers never finish
        assert _serviceUntil(server, lambda: server.servant.ixes)

        for _ in range(8):
            tymist.tick()
            server.service()  # raised RuntimeError: dict changed size
        assert not server.servant.ixes
        assert not server.stewards
    finally:
        sock.close()
        server.servant.close()


def test_http_server_without_tymist_serves_request():
    """
    A server serviced by hand with no tymth wound has no tyme. Its connections
    must never be timed out and servicing them must not raise.
    """
    port = 6436
    server = http.Server(port=port, app=_okApp, tymeout=1.0)  # no tymth
    server.servant.reopen()
    sock = socket.create_connection(("127.0.0.1", port))
    try:
        sock.sendall(b"GET / HTTP/1.1\r\nHost: loc\r\nContent-Length: 0\r\n\r\n")
        data = _recvAll(sock, server, until=b"\r\n\r\nok")
        assert data.startswith(b"HTTP/1.1 200 OK")
        assert data.endswith(b"\r\n\r\nok")
        server.service()
        assert server.servant.ixes  # persistent and never timed out
    finally:
        sock.close()
        server.close()


def test_http_server_drops_idle_persistent_connection():
    """
    An HTTP/1.1 keep-alive connection that finished a request and then sits
    idle is dropped after tymeout. It used to have its tymeout set to 0.0 as
    soon as its headers were parsed, so it was never dropped.
    """
    tymist = tyming.Tymist(tock=0.25)
    port = 6437
    server = http.Server(port=port, app=_okApp, tymth=tymist.tymen(), tymeout=1.0)
    server.servant.reopen()
    sock = socket.create_connection(("127.0.0.1", port))
    try:
        sock.sendall(b"GET / HTTP/1.1\r\nHost: loc\r\nContent-Length: 0\r\n\r\n")
        data = _recvAll(sock, server, until=b"\r\n\r\nok")
        assert data.endswith(b"\r\n\r\nok")
        assert server.servant.ixes  # kept alive for the next request

        for _ in range(3):  # 0.75 s idle
            tymist.tick()
            server.service()
        assert server.servant.ixes

        for _ in range(2):  # 1.25 s idle
            tymist.tick()
            server.service()
        assert not server.servant.ixes
    finally:
        sock.close()
        server.close()


@pytest.mark.parametrize("port, connection", [(6438, b"close"),
                                              (6440, b"keep-alive")])
def test_http_server_keeps_long_poll_response(port, connection):
    """
    A response in progress whose iterable yields b'' while it waits (a long
    poll or event stream) sends no bytes, but must not be cut by the idle
    tymeout, whether or not the connection is persistent.
    """
    state = dict(done=False)

    def longPollApp(environ, start_response):
        start_response("200 OK", [("Content-Type", "text/event-stream")])
        while not state["done"]:
            yield b""
        yield b"data: done\n\n"

    tymist = tyming.Tymist(tock=0.25)
    server = http.Server(port=port, app=longPollApp, tymth=tymist.tymen(), tymeout=1.0)
    server.servant.reopen()
    sock = socket.create_connection(("127.0.0.1", port))
    try:
        sock.sendall(b"GET /poll HTTP/1.1\r\nHost: loc\r\nConnection: "
                     + connection + b"\r\n\r\n")
        assert _serviceUntil(server, lambda: server.reps)  # response started

        for _ in range(16):  # four virtual seconds of waiting, 4x tymeout
            tymist.tick()
            server.service()
            assert server.servant.ixes  # in-progress response is not idle
        assert server.reps and not next(iter(server.reps.values())).ended

        state["done"] = True
        data = _recvAll(sock, server, until=b"data: done\n\n")
        assert b"data: done\n\n" in data
    finally:
        sock.close()
        server.close()


def localTestCertDirPath():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certs')


def test_tls_server_drops_connection_without_handshake():
    """
    A client that opens TCP to a ServerTls and never sends a ClientHello is
    dropped from .cxes once tymeout passes, instead of holding an fd forever.
    """
    certDirPath = localTestCertDirPath()
    tymist = tyming.Tymist(tock=0.25)
    port = 6439
    with tcp.openServer(cls=tcp.ServerTls,
                        tymth=tymist.tymen(),
                        ha=("", port),
                        tymeout=1.0,
                        keypath=os.path.join(certDirPath, 'server_key.pem'),
                        certpath=os.path.join(certDirPath, 'server_cert.pem'),
                        cafilepath=os.path.join(certDirPath, 'client.pem')) as server:
        sock = socket.create_connection(("127.0.0.1", port))
        try:
            for _ in range(50):
                server.serviceConnects()
                if server.cxes:
                    break
                time.sleep(0.02)
            assert server.cxes  # accepted, handshake pending
            cx = next(iter(server.cxes.values()))

            for _ in range(3):  # 0.75 s
                tymist.tick()
                server.serviceConnects()
            assert server.cxes

            for _ in range(2):  # 1.25 s
                tymist.tick()
                server.serviceConnects()
            assert not server.cxes
            assert not server.ixes
            assert cx.cs is None  # socket closed

            sock.settimeout(1.0)
            assert sock.recv(1) == b""  # far side sees the close
        finally:
            sock.close()
