# -*- encoding: utf-8 -*-
"""
tests.core.http.test_oversize_413_response

A request refused by the body cap must be answered with the 413 the exception
carries, on both server paths.

Parsent.parseMessage caught the HTTPException and kept only str(ex), so
RequestEntityTooLarge.status was discarded. Server.serviceReqs then closed the
connection with no response, and BareServer.serviceStewards did not check
.errored at all: it saw .ended and called Steward.respond, answering 200 to a
request whose body it had refused and never read.
"""
import socket
import time

import pytest

from hio.base import doing
from hio.core import http
from hio.core.http import serving, httping


CAP = serving.Requestant.MaxBody


def _send_oversize(server):
    """Open a connection, declare an over-cap body, return the bytes received."""
    server.servant.reopen()
    port = server.servant.eha[1]
    sock = socket.create_connection(("127.0.0.1", port))
    sock.settimeout(0.2)
    got = bytearray()
    try:
        sock.sendall(b"POST / HTTP/1.1\r\n"
                     b"Host: localhost\r\n"
                     b"Content-Length: %d\r\n\r\n" % (CAP + 1))
        sock.sendall(b"A" * 1000)  # only a little of the declared body
        for _ in range(40):
            server.service()
            try:
                data = sock.recv(4096)
                if not data:
                    break
                got.extend(data)
            except (socket.timeout, BlockingIOError):
                pass
            time.sleep(0.01)
    finally:
        sock.close()
        server.servant.close()
    return bytes(got)


def test_packErrorResponse():
    """The helper builds a complete response that closes the connection."""
    raw = httping.packErrorResponse(413, detail="too big")
    head, _, body = raw.partition(b"\r\n\r\n")
    assert head.startswith(b"HTTP/1.1 413 Request Entity Too Large")
    assert b"Connection: close" in head
    assert b"Content-Length: 7" in head
    assert body == b"too big"
    """End Test"""


def test_wsgi_server_answers_413():
    """The WSGI path answers 413 rather than dropping the connection."""
    def wsgiApp(environ, start_response):  # must never run
        start_response("200 OK", [("Content-Length", "2")])
        return [b"ok"]

    doist = doing.Doist(tock=0.03125, real=True, limit=1.0)
    got = _send_oversize(http.Server(port=6203, app=wsgiApp,
                                     tymth=doist.tymen()))
    assert got.startswith(b"HTTP/1.1 413 "), got[:64]
    """End Test"""


def test_bare_server_answers_413_not_200():
    """The bare path answers 413 and never reports the refused request as OK."""
    doist = doing.Doist(tock=0.03125, real=True, limit=1.0)
    got = _send_oversize(serving.BareServer(port=6204, tymth=doist.tymen()))
    assert not got.startswith(b"HTTP/1.1 200"), got[:64]
    assert got.startswith(b"HTTP/1.1 413 "), got[:64]
    """End Test"""


if __name__ == '__main__':
    test_packErrorResponse()
    test_wsgi_server_answers_413()
    test_bare_server_answers_413_not_200()
