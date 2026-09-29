# -*- encoding: utf-8 -*-
"""
tests.core.http.test_chunk_extension

parseChunk stored chunk-extension parameters as ``parms[name.strip()] = ...``,
where name is a slice of a bytearray and so is itself a bytearray. bytearray is
unhashable, so any chunk extension raised TypeError.

TypeError is not an HTTPException, so it passed straight through
Parsent.parseMessage's ``except HTTPException`` and through
Server.serviceReqs's ``except httping.HTTPException``, out of Server.service()
and into the caller's run loop.

Chunk extensions are legal HTTP/1.1 (RFC 9112 section 7.1.1).
"""
import socket
import time

from hio.base import doing
from hio.core import http
from hio.core.http import httping


def test_parse_chunk_extension_parms():
    """A chunk extension parses into hashable keys and values."""
    raw = bytearray(b"1;foo=bar;baz\r\nA\r\n")
    parser = httping.parseChunk(raw=raw)
    while True:
        result = next(parser)
        if result is not None:
            parser.close()
            break

    size, parms, trails, chunk = result
    assert size == 1
    assert chunk == bytearray(b"A")
    assert parms == {b"foo": b"bar", b"baz": None}
    hash(next(iter(parms)))  # keys must be hashable at all
    """End Test"""


def test_chunk_extension_does_not_crash_server():
    """A request carrying a chunk extension does not propagate out of service().

    The harm is a crash of the whole server loop, so the assertion is that
    service() returns normally; whether the request is answered or refused is
    not what this test pins.
    """
    def wsgiApp(environ, start_response):
        start_response("200 OK", [("Content-type", "text/plain"),
                                  ("Content-length", "2")])
        return [b"ok"]

    port = 6199
    doist = doing.Doist(tock=0.03125, real=True, limit=1.0)
    server = http.Server(port=port, app=wsgiApp, tymth=doist.tymen())
    server.servant.reopen()

    sock = socket.create_connection(("127.0.0.1", port))
    try:
        sock.sendall(b"POST / HTTP/1.1\r\n"
                     b"Host: localhost\r\n"
                     b"Transfer-Encoding: chunked\r\n"
                     b"\r\n"
                     b"1;a=b\r\nX\r\n"  # one chunk WITH an extension parameter
                     b"0\r\n\r\n")
        for _ in range(30):
            server.service()  # TypeError escaped here before the fix
            time.sleep(0.02)
    finally:
        sock.close()
        server.servant.close()
    """End Test"""


if __name__ == '__main__':
    test_parse_chunk_extension_parms()
    test_chunk_extension_does_not_crash_server()
