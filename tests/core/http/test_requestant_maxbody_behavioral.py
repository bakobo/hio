# -*- encoding: utf-8 -*-
"""
tests.core.http.test_requestant_maxbody_behavioral

BEHAVIORAL regression for issue 9 (unbounded HTTP request body on the hio
server). Drives hio.core.http.serving.Requestant.parseBody directly with a
declared Content-Length of 8 MiB.

References ONLY symbols present in BOTH hio trees:
    hio.core.http.serving.Requestant          (class)
    Requestant.parseBody                       (generator)
    .msg .length .chunked .bodied .closed .body (Parsent attributes)
    hio.core.http.httping.HTTPException         (base exception)

The Requestant is constructed the SAME way in both trees (no maxBody kwarg), so
the patched default cap (4 MiB class attribute .MaxBody) applies. On UNPATCHED
hio, parseBody accumulates the full 8 MiB into .body (the harm). On PATCHED hio,
parseBody raises httping.RequestEntityTooLarge (a subclass of HTTPException)
before buffering anything.

The behavioral red is `assert accumulated < 8 MiB`: on unpatched .body holds the
full 8 MiB (AssertionError); on patched the request is rejected before the copy.
"""
from hio.core.http import serving, httping

BODY_SIZE = 8 * 1024 * 1024  # 8 MiB, over the patched 4 MiB default cap


def _drive(gen):
    """Run a parseBody generator to completion, returning nothing."""
    try:
        while True:
            next(gen)
    except StopIteration:
        pass


def test_requestant_parsebody_does_not_buffer_oversized_request():
    req = serving.Requestant(remoter=None)  # identical construction, both trees
    req.msg = bytearray(b"B" * BODY_SIZE)
    req.length = BODY_SIZE
    req.chunked = False
    req.bodied = False
    req.closed = False

    try:
        _drive(req.parseBody())
        accumulated = len(req.body)
    except httping.HTTPException:
        # patched: rejected (RequestEntityTooLarge) before buffering the body
        accumulated = 0

    # HARM on unpatched: the full 8 MiB request body is buffered into .body.
    assert accumulated < BODY_SIZE, (
        f"request body of {accumulated} bytes was fully buffered instead of "
        f"being rejected over the size cap")
