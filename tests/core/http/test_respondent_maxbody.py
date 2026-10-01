# -*- encoding: utf-8 -*-
"""
tests.core.http.test_respondent_maxbody

Respondent bounds the size of a response body it will hold, mirroring the
Requestant.maxBody limit on the server side.
"""
from hio.core.http import clienting, httping


def _respond(raw, **kwa):
    """Parse raw response bytes with a fresh Respondent until it ends."""
    resp = clienting.Respondent(msg=bytearray(raw), **kwa)
    for _ in range(10000):
        resp.parse()
        if resp.ended:
            break
    return resp


def _head(extra):
    return b"HTTP/1.1 200 OK\r\n" + extra + b"\r\n"


def test_default_maxbody():
    assert clienting.Respondent.MaxBody == 16 * 1024 * 1024
    assert clienting.Respondent().maxBody == clienting.Respondent.MaxBody


def test_content_length_over_limit_is_refused_before_buffering():
    # declares far more than it sends, so a refusal must come from the header
    raw = _head(b"Content-Length: 1000000\r\n") + b"x" * 10
    resp = _respond(raw, maxBody=100)
    assert resp.ended
    assert resp.errored
    assert len(resp.body) == 0


def test_content_length_within_limit_is_accepted():
    raw = _head(b"Content-Length: 10\r\n") + b"x" * 10
    resp = _respond(raw, maxBody=100)
    assert not resp.errored
    assert bytes(resp.body) == b"x" * 10


def test_chunked_over_limit_is_refused():
    chunk = b"40\r\n" + b"y" * 64 + b"\r\n"
    raw = _head(b"Transfer-Encoding: chunked\r\n") + chunk * 4 + b"0\r\n\r\n"
    resp = _respond(raw, maxBody=100)
    assert resp.errored
    assert len(resp.body) <= 100


def test_single_oversized_chunk_is_refused_before_its_data_arrives():
    raw = _head(b"Transfer-Encoding: chunked\r\n") + b"100000\r\n" + b"z" * 10
    resp = _respond(raw, maxBody=100)
    assert resp.errored
    assert len(resp.body) == 0


def test_unknown_length_over_limit_is_refused():
    raw = _head(b"") + b"w" * 500
    resp = clienting.Respondent(msg=bytearray(raw), maxBody=100)
    for _ in range(100):
        resp.parse()
        if resp.ended:
            break
    assert resp.errored
    assert len(resp.body) <= 600  # never grows past one read beyond the cap


def test_maxbody_zero_disables_limit():
    raw = _head(b"Content-Length: 500\r\n") + b"v" * 500
    resp = _respond(raw, maxBody=0)
    assert not resp.errored
    assert len(resp.body) == 500


def test_client_passes_maxbody_and_drops_connection_on_overflow():
    client = clienting.Client(hostname="127.0.0.1", port=6101, maxBody=100,
                              reconnectable=False)
    assert client.respondent.maxBody == 100
    client.waited = True
    client.connector.rxbs.extend(_head(b"Content-Length: 1000000\r\n") + b"x" * 10)
    client.connector.serviceReceives = lambda: None  # no socket in this test
    closed = []
    client.connector.close = lambda: closed.append(True)
    client.serviceResponse()
    for _ in range(10):
        if client.responses:
            break
        client.serviceResponse()
    assert client.responses
    response = client.responses[0]
    assert response["errored"]
    assert closed  # unread body bytes must not be parsed as the next response
    assert len(client.connector.rxbs) == 0
