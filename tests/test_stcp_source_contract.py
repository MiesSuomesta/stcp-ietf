#!/usr/bin/env python3
"""Check that the independently specified STCP vectors match source constants.

Usage:
  STCP_SOURCE=/path/to/STCP python3 -m unittest discover -s tests -p 'test_stcp_source_contract.py' -v
  STCP_SOURCE=/path/to/stcp-source.zip python3 -m unittest discover -s tests -p 'test_stcp_source_contract.py' -v

STCP_SOURCE is intentionally required. Without it, the test is skipped, not
reported as a pass. This is a source-contract check, NOT a kernel execution test.
"""
import os
import pathlib
import re
import unittest
import zipfile

SOURCE = os.environ.get("STCP_SOURCE", "")

def read_source(suffix):
    path = pathlib.Path(SOURCE)
    if path.is_dir():
        target = path / suffix
        if not target.is_file():
            raise FileNotFoundError(target)
        return target.read_text(encoding="utf-8")
    if path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            matches = [name for name in archive.namelist()
                       if name == suffix or name.endswith("/" + suffix)]
            if len(matches) != 1:
                raise ValueError("Expected exactly one " + suffix + " in archive")
            return archive.read(matches[0]).decode("utf-8")
    raise FileNotFoundError("STCP_SOURCE must be a source directory or ZIP: " + SOURCE)

@unittest.skipUnless(SOURCE, "Set STCP_SOURCE to actual STCP source directory or ZIP")
class SourceContractTests(unittest.TestCase):
    def test_frame_constants(self):
        source = read_source("kernel/module/rust/src/frame.rs")
        self.assertRegex(source, r"STCP_HEADER_LEN\s*:\s*usize\s*=\s*17\s*;")
        for name, number in {
            "PublicKey": 1, "HandshakeDone": 2, "DataChunk": 3,
            "Ack": 5, "Ping": 6, "Pong": 7, "Close": 8, "Reset": 9,
        }.items():
            with self.subTest(packet_type=name):
                self.assertRegex(source, rf"\b{re.escape(name)}\s*=\s*{number}\s*,")

    def test_kdf_domain_and_labels(self):
        source = read_source("kernel/module/src/stcp_crypto.c")
        for name, literal in {
            "domain": "STCPv4-AES256-GCM-HKDF-SHA256",
            "client_label": "STCPv4 AES256-GCM client to server key",
            "server_label": "STCPv4 AES256-GCM server to client key",
        }.items():
            with self.subTest(label=name):
                self.assertRegex(source, rf'\b{re.escape(name)}\[\]\s*=\s*"{re.escape(literal)}"\s*;')

if __name__ == "__main__":
    unittest.main()
