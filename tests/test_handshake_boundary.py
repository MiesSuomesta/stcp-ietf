#!/usr/bin/env python3
"""Source-contract and deterministic model tests; NOT live kernel/Zephyr execution."""
import argparse
from pathlib import Path
import unittest

def parse_model(frames, boundary):
    key = done = False
    consumed = []
    for frame in frames:
        if boundary and key and done:
            break
        consumed.append(frame)
        if frame == "PublicKey":
            key = True
        elif frame == "HandshakeDone":
            done = True
        else:
            return "Protocol", consumed
    return ("Ready" if key and done else "Handshake"), consumed

class Tests(unittest.TestCase):
    def test_key_done_data(self):
        seq = ["PublicKey", "HandshakeDone", "DataChunk"]
        self.assertEqual(parse_model(seq, True), ("Ready", seq[:2]))
        self.assertEqual(parse_model(seq, False), ("Protocol", seq))
    def test_done_key_data(self):
        seq = ["HandshakeDone", "PublicKey", "DataChunk"]
        self.assertEqual(parse_model(seq, True), ("Ready", seq[:2]))
        self.assertEqual(parse_model(seq, False), ("Protocol", seq))
    def test_completed_handshake(self):
        seq = ["PublicKey", "HandshakeDone"]
        self.assertEqual(parse_model(seq, True), ("Ready", seq))
        self.assertEqual(parse_model(seq, False), ("Ready", seq))
    def test_early_data(self):
        seq = ["PublicKey", "DataChunk", "HandshakeDone"]
        self.assertEqual(parse_model(seq, True)[0], "Protocol")
        self.assertEqual(parse_model(seq, False)[0], "Protocol")
    def test_actual_source_contract(self):
        linux = Path(self.linux).read_text()
        zephyr = Path(self.zephyr).read_text()
        l = linux.split("fn process_handshake_frames_locked(", 1)[1].split("pub fn create_external_tcp_child(", 1)[0]
        z = zephyr.split("fn process_handshake_frames(", 1)[1].split("pub fn accept(", 1)[0]
        self.assertIn("let have_handshake_inputs", l)
        self.assertLess(l.index("if have_handshake_inputs {"), l.index("extract_next_wire_frame(ctx,queue)"))
        self.assertIn("let have_handshake_inputs", z)
        self.assertIn("received_done || inner.peer_handshake_done", z)
        self.assertIn("received_key.is_some() || inner.crypto.ready()", z)
        self.assertLess(z.index("if have_handshake_inputs {"), z.index("extract_next_wire_frame(ctx,queue)"))
        for parser in (l, z):
            self.assertIn("inner.crypto.ready() && inner.peer_handshake_done", parser)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--linux", required=True)
    p.add_argument("--zephyr", required=True)
    args = p.parse_args()
    Tests.linux, Tests.zephyr = args.linux, args.zephyr
    unittest.main(argv=["test_handshake_boundary.py"], verbosity=2)
