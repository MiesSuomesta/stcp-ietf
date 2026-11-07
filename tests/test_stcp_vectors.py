#!/usr/bin/env python3
"""Independent STCP known-answer tests. Run: python3 -m unittest -v tests/test_stcp_vectors.py
Requires: pip install cryptography. NOT a Linux-kernel/Zephyr integration test.
Source basis: Linux STCP module snapshot 2026-11-02 (frame.rs, stcp_crypto.c).
"""
import hashlib
import hmac
import unittest
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

EXPECTED = {
    "client_public": "8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a",
    "server_public": "de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f",
    "shared": "4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742",
    "salt": "68789ffabafa9cb7c2895c3a211ef17aadbdc15a22669984f0cfdfbeddcc6fdd",
    "prk": "6bd56a3c28264f96f858a078e0a34e5002cc39f6e8cbe0f8ed6b724fbacbb9aa",
    "c2s": "4a78b69f86818b6027f82f9b21cfa799083898eaa988d9ef70ce8ddff650c62e",
    "s2c": "a58ede41164232df21c8d31852d0c7863afb9ca54defd3126615d63f5d280e51",
    "control": "a7870e1b81b0f5f850f06a429ebbadbae20c9bbcd7806141c0c2bdd25d16ae88",
    "data": "330000001d00000001000000001234567800000000000000018f577af326079aae12b967b491f1edf9a00ff91477",
    "ack": "350000001800000000000000011234567800000000000000012ee2a428086309e892dd4d9cb4c97715",
}

def frame_header(packet_type, payload_length, seq=0, ack=0, conn_id=0, flags=0):
    assert 1 <= packet_type <= 9 and 0 <= flags <= 3
    assert all(0 <= x <= 0xffffffff for x in (payload_length, seq, ack, conn_id))
    return bytes([(flags << 6) | (3 << 4) | packet_type]) + b"".join(
        x.to_bytes(4, "big") for x in (payload_length, seq, ack, conn_id)
    )

def keys():
    client = X25519PrivateKey.from_private_bytes(bytes.fromhex(
        "77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a"))
    server = X25519PrivateKey.from_private_bytes(bytes.fromhex(
        "5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb"))
    cp = client.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    sp = server.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    shared = client.exchange(server.public_key())
    salt = hashlib.sha256(b"STCPv4-AES256-GCM-HKDF-SHA256" + cp + sp).digest()
    prk = hmac.digest(salt, shared, "sha256")
    c2s = hmac.digest(prk, b"STCPv4 AES256-GCM client to server key\x01", "sha256")
    s2c = hmac.digest(prk, b"STCPv4 AES256-GCM server to client key\x01", "sha256")
    control = hmac.digest(c2s, b"STCP wire3 control AES256-GCM key\x01", "sha256")
    return dict(client_public=cp, server_public=sp, shared=shared, salt=salt,
                prk=prk, c2s=c2s, s2c=s2c, control=control)

class STCPVectorTests(unittest.TestCase):
    def test_x25519_and_kdf(self):
        for name, value in keys().items():
            with self.subTest(name=name):
                self.assertEqual(value.hex(), EXPECTED[name])

    def test_data_frame(self):
        hdr = frame_header(3, 29, 1, 0, 0x12345678)
        nonce = (1).to_bytes(8, "big")
        result = AESGCM(keys()["c2s"]).encrypt(b"\x00" * 4 + nonce, b"hello", hdr)
        self.assertEqual((hdr + nonce + result).hex(), EXPECTED["data"])
        self.assertEqual(AESGCM(keys()["c2s"]).decrypt(b"\x00" * 4 + nonce, result, hdr), b"hello")

    def test_ack_frame(self):
        hdr = frame_header(5, 24, 0, 1, 0x12345678)
        nonce = (1).to_bytes(8, "big")
        tag = AESGCM(keys()["control"]).encrypt(b"\x00" * 4 + nonce, b"", hdr)
        self.assertEqual((hdr + nonce + tag).hex(), EXPECTED["ack"])
        self.assertEqual(AESGCM(keys()["control"]).decrypt(b"\x00" * 4 + nonce, tag, hdr), b"")

    def test_header_flags_and_endianness(self):
        self.assertEqual(frame_header(1, 32, 0x01020304, 0x05060708, 0x090a0b0c, 2).hex(),
                         "b1000000200102030405060708090a0b0c")

    def test_public_key_frame_32_octets(self):
        # Current STCP PublicKey format: unpadded X25519 public key.
        public = keys()["client_public"]
        self.assertEqual(len(public), 32)
        header = frame_header(1, len(public), flags=2)
        frame = header + public
        self.assertEqual(len(frame), 49)
        self.assertEqual(header.hex(), "b100000020000000000000000000000000")
        self.assertEqual(frame[17:], public)
        self.assertEqual(int.from_bytes(frame[1:5], "big"), 32)

    def test_aead_tampering_rejected(self):
        for tamper_offset in (5, -1):
            frame = bytearray.fromhex(EXPECTED["data"])
            frame[tamper_offset] ^= 1
            with self.subTest(offset=tamper_offset), self.assertRaises(Exception):
                AESGCM(keys()["c2s"]).decrypt(b"\x00" * 4 + frame[17:25],
                                                bytes(frame[25:]), bytes(frame[:17]))

if __name__ == "__main__":
    unittest.main()
