#!/usr/bin/env python3
"""STCPv3 deterministic wire-queue boundary model.

Uses real 17-byte STCP frame layout, but DOES NOT invoke the production
Rust parser or decrypt DATA. HB-01/HB-02 integration status remains NOT RUN.
"""
import os
from pathlib import Path
import struct
import unittest

HEADER = struct.Struct("!BIIII")
PUBLIC_KEY, HANDSHAKE_DONE, DATA_CHUNK = 1, 2, 3

def frame(kind, payload=b"", connection_id=1):
    return HEADER.pack((3 << 4) | kind, len(payload), 0, 0, connection_id) + payload

def peek(queue):
    if len(queue) < HEADER.size:
        return None
    descriptor, length, _, _, _ = HEADER.unpack_from(queue)
    if (descriptor >> 4) & 3 != 3:
        raise ValueError("bad version")
    kind = descriptor & 15
    if kind not in (PUBLIC_KEY, HANDSHAKE_DONE, DATA_CHUNK):
        raise ValueError("unexpected type")
    if len(queue) < HEADER.size + length:
        return None
    return kind, length, HEADER.size + length

def consume_handshake(queue, persisted_done=False, crypto_ready=False):
    """Executable boundary model of the source's pre-extraction condition."""
    received_key = received_done = False
    consumed = []
    while not ((received_done or persisted_done) and (received_key or crypto_ready)):
        next_frame = peek(queue)
        if next_frame is None:
            break
        kind, length, total = next_frame
        if kind == PUBLIC_KEY:
            if length != 64:
                raise ValueError("invalid PublicKey")
            received_key = True
        elif kind == HANDSHAKE_DONE:
            if length:
                raise ValueError("invalid HandshakeDone")
            received_done = True
        else:
            raise ValueError("DATA before handshake boundary")
        consumed.append(kind)
        del queue[:total]
    return (received_done or persisted_done) and (received_key or crypto_ready), consumed

class Tests(unittest.TestCase):
    def setUp(self):
        self.key = frame(PUBLIC_KEY, bytes(range(64)))
        self.done = frame(HANDSHAKE_DONE)
        # Opaque sentinel only: NOT valid negotiated AES-GCM ciphertext.
        self.data = frame(DATA_CHUNK, b"OPAQUE-NOT-VALID-AEAD")

    def assert_boundary(self, wire, expected):
        queue = bytearray(wire)
        ready, consumed = consume_handshake(queue)
        self.assertTrue(ready)
        self.assertEqual(consumed, expected)
        self.assertEqual(bytes(queue), self.data)

    def test_hb01_key_done_data_same_queue(self):
        self.assert_boundary(self.key + self.done + self.data, [PUBLIC_KEY, HANDSHAKE_DONE])

    def test_hb02_done_key_data_same_queue(self):
        self.assert_boundary(self.done + self.key + self.data, [HANDSHAKE_DONE, PUBLIC_KEY])

    def test_done_persisted_across_calls(self):
        queue = bytearray(self.done)
        self.assertEqual(consume_handshake(queue), (False, [HANDSHAKE_DONE]))
        queue.extend(self.key + self.data)
        self.assertEqual(consume_handshake(queue, persisted_done=True), (True, [PUBLIC_KEY]))
        self.assertEqual(bytes(queue), self.data)

    def test_split_header_and_payload(self):
        queue = bytearray(self.key[:8])
        self.assertEqual(consume_handshake(queue), (False, []))
        queue.extend(self.key[8:] + self.done + self.data)
        self.assertEqual(consume_handshake(queue), (True, [PUBLIC_KEY, HANDSHAKE_DONE]))
        self.assertEqual(bytes(queue), self.data)

    def test_early_data_rejected(self):
        with self.assertRaisesRegex(ValueError, "DATA before"):
            consume_handshake(bytearray(self.key + self.data + self.done))

    def test_actual_source_guard(self):
        paths = [os.environ.get("STCP_LINUX_SESSION"), os.environ.get("STCP_ZEPHYR_SESSION")]
        if not all(paths):
            self.skipTest("Set STCP_LINUX_SESSION and STCP_ZEPHYR_SESSION")
        for path, name, end in zip(paths,
                                   ["process_handshake_frames_locked", "process_handshake_frames"],
                                   ["pub fn create_external_tcp_child(", "pub fn accept("]):
            source = Path(path).read_text(encoding="utf-8")
            parser = source.split("fn " + name + "(", 1)[1].split(end, 1)[0]
            self.assertLess(parser.index("if have_handshake_inputs {"),
                            parser.index("extract_next_wire_frame(ctx,queue)"))
            self.assertIn("received_done || inner.peer_handshake_done", parser)
            self.assertIn("received_key.is_some() || inner.crypto.ready()", parser)

if __name__ == "__main__":
    unittest.main(verbosity=2)
