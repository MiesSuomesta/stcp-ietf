#!/usr/bin/env python3
"""Source-contract and deterministic model tests; NOT live kernel/Zephyr execution."""
import argparse
import os
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
        linux_path = os.environ.get("STCP_LINUX_SESSION")
        zephyr_path = os.environ.get("STCP_ZEPHYR_SESSION")
        if not linux_path or not zephyr_path:
            self.skipTest("Set STCP_LINUX_SESSION and STCP_ZEPHYR_SESSION to inspect real sources")
        linux = Path(linux_path).read_text(encoding="utf-8")
        zephyr = Path(zephyr_path).read_text(encoding="utf-8")
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
    p.add_argument("--linux", help="Linux kernel STCP session.rs")
    p.add_argument("--zephyr", help="Zephyr STCP session.rs")
    args = p.parse_args()
    if bool(args.linux) != bool(args.zephyr):
        p.error("--linux and --zephyr must be provided together")
    if args.linux:
        os.environ["STCP_LINUX_SESSION"] = args.linux
        os.environ["STCP_ZEPHYR_SESSION"] = args.zephyr
    unittest.main(argv=["test_handshake_boundary.py"], verbosity=2)
