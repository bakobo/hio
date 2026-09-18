# -*- encoding: utf-8 -*-
"""
tests.core.http.test_respondent_unbounded

EXPLICITLY UNFIXED gap (issue 10, hio client). hio.core.http.clienting.Respondent
buffers HTTP RESPONSE bodies with the identical unbounded pattern as the server's
Requestant, and NEITHER tree fixes it. In both hio trees, the known-content-length
branch of Respondent.parseBody does:

    src/hio/core/http/clienting.py:582-583 (patched) / :583 (unpatched)
        while len(self.msg) < self.length:
            ...
        self.body = self.msg[:self.length]

with no size ceiling (the streaming/else branch likewise does
`self.body.extend(self.msg[:])` unbounded). The MaxBody cap added to the server
(serving.Requestant) has no counterpart here.

This test drives the real Respondent.parseBody with an 8 MiB response body and
asserts the client bounds it. It FAILS on BOTH trees because the copy is
unbounded, so it is marked xfail(strict=False) to record the gap while keeping
the suite green. Shared symbols only: hio.core.http.clienting.Respondent /
.parseBody and hio.core.http.httping.HTTPException.
"""
import pytest

from hio.core.http import clienting, httping

BODY_SIZE = 8 * 1024 * 1024  # 8 MiB response body


def _drive(gen):
    try:
        while True:
            next(gen)
    except StopIteration:
        pass


@pytest.mark.xfail(reason="unfixed: Respondent.parseBody buffers responses "
                          "unbounded; no patch prepared "
                          "(clienting.py:582-583 copies self.msg[:self.length] "
                          "with no size cap)",
                   strict=False)
def test_respondent_parsebody_bounds_oversized_response():
    resp = clienting.Respondent()
    resp.msg = bytearray(b"C" * BODY_SIZE)
    resp.length = BODY_SIZE
    resp.chunked = False
    resp.bodied = False
    resp.closed = False

    try:
        _drive(resp.parseBody())
        accumulated = len(resp.body)
    except httping.HTTPException:
        accumulated = 0

    # A bounded client would reject/truncate; unbounded copy buffers the full
    # 8 MiB. Recorded gap: fails on BOTH trees (xfail).
    assert accumulated < BODY_SIZE, (
        f"response body of {accumulated} bytes was fully buffered with no "
        f"size ceiling")
