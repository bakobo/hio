# -*- encoding: utf-8 -*-
"""
tests.core.http.test_requestant_maxbody_single_chunk

The chunked-transfer branch of Requestant.parseBody checks the cap as
``len(self.body) + size > self.maxBody``, but only after httping.parseChunk
returns, and parseChunk does not return until the whole chunk is in .msg
(``while len(raw) < size: yield None``). A single chunk whose size line declares
more than maxBody is therefore buffered in full before it is rejected.

The chunk size is known as soon as the chunk-size line has been read, so the
request can be rejected at that point, before any chunk data is buffered.

The test feeds .msg incrementally, the way Remoter.serviceReceives extends
rxbs from the socket, and steps the parser after each feed. It records the
peak number of bytes .msg held before the 413 was raised. The peak is what
matters: parseChunk deletes the chunk from .msg on its way out, so .msg is
nearly empty at the moment the exception fires.
"""
import pytest

from hio.core.http import serving, httping

MAX_BODY = serving.Requestant.MaxBody  # 4 MiB default
CHUNK_SIZE = 4 * MAX_BODY  # one chunk declaring 16 MiB
FEED = 64 * 1024  # bytes delivered per receive


def test_single_oversized_chunk_rejected_before_buffering():
    msg = bytearray()
    req = serving.Requestant(msg=msg, remoter=None)
    req.chunked = True
    req.length = None
    req.headed = True

    parser = req.parseBody()
    msg.extend(format(CHUNK_SIZE, "x").encode("ascii") + b"\r\n")

    peak = 0
    sent = 0
    with pytest.raises(httping.HTTPException) as exc:
        while True:
            peak = max(peak, len(msg) + len(req.body))
            next(parser)
            if sent >= CHUNK_SIZE + 2:
                msg.extend(b"0\r\n\r\n")  # terminate so an unbounded parser ends
                sent = -1
            elif sent >= 0:
                msg.extend(b"C" * FEED)
                sent += FEED
                if sent >= CHUNK_SIZE:
                    msg.extend(b"\r\n")
                    sent = CHUNK_SIZE + 2
            else:
                break  # parser finished without rejecting

    assert exc.value.status == 413
    # HARM on the fix as written: the full 16 MiB chunk was held in .msg
    # before the 413, so the cap bounded nothing for this request.
    assert peak <= MAX_BODY, (
        f"{peak} bytes buffered before a chunk declaring {CHUNK_SIZE} bytes "
        f"was rejected; cap is {MAX_BODY}")
