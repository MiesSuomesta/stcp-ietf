#!/usr/bin/env python3
"""Independent STCP wire3 header and key-derivation reference vectors.

Run: python3 tests/vectors/verify_wire3_kdf.py
Requires: cryptography (Python package).
These are reference vectors from the draft, NOT yet confirmed against Linux/Zephyr.
"""
import hashlib
import hmac

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def check(name, actual, expected):
    assert actual.hex() == expected, f"{name}: got {actual.hex()}, expected {expected}"
    print(f"PASS {name}: {actual.hex()}")


def main():
    # descriptor: type=3 (DataChunk), version=3, flags=0.
    header = bytes([0x33]) + (32).to_bytes(4, "big") + (1).to_bytes(4, "big") + (0).to_bytes(4, "big") + (0x12345678).to_bytes(4, "big")
    check("header", header, "3300000020000000010000000012345678")
    assert len(header) == 17

    # Deterministic, public test-only private scalars. NEVER use as live keys.
    client_private = bytes.fromhex("77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a")
    server_private = bytes.fromhex("5dab087e624a8a4b79e17f8b83800ee6f2a6f43fbc9b9b31e8a5e9b45d0a1c0b")
    client = X25519PrivateKey.from_private_bytes(client_private)
    server = X25519PrivateKey.from_private_bytes(server_private)
    client_public = client.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    server_public = server.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    check("client_public", client_public, "8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a")
    check("server_public", server_public, "aca3aed7f7514cd8b475b6cf205d9319430ccd410b707caddb36a2966f280447")

    shared = client.exchange(server.public_key())
    assert shared == server.exchange(client.public_key())
    check("shared_secret", shared, "e0b384cd744f9545df2d29b7f5f779519b49a27a689d0600e8e4d78802dbe212")
    salt = hashlib.sha256(b"STCPv4-AES256-GCM-HKDF-SHA256" + client_public + server_public).digest()
    check("salt", salt, "f43806e76c966b00fbe7074f922d6ddf9a4a2e829fe824e9ea826b800aa2345b")
    prk = hmac.new(salt, shared, hashlib.sha256).digest()
    check("prk", prk, "a7f64edcf9736b4076ce6cd77c92dd605cd6f9b47cd697d45390da4486aa39df")
    c2s = hmac.new(prk, b"STCPv4 AES256-GCM client to server key\x01", hashlib.sha256).digest()
    s2c = hmac.new(prk, b"STCPv4 AES256-GCM server to client key\x01", hashlib.sha256).digest()
    check("client_to_server", c2s, "edf593cddf1439b731496f3743ed14c71e2bd654fccf838e4119e49708d7e2bb")
    check("server_to_client", s2c, "499a4576638d783d415a6504ecbaae3c61aa6eb3da8b7b8d9b9404193b8246fb")
    control_label = b"STCP wire3 control AES256-GCM key\x01"
    check("client_control", hmac.new(c2s, control_label, hashlib.sha256).digest(), "213db01c7f1fcc65af75659b0b9578f64526caf04e62132215b2c9db39927799")
    check("server_control", hmac.new(s2c, control_label, hashlib.sha256).digest(), "0fe127aec8abf02645ca630084688d01dea9c53a29e5a3b379cebb23ab16a986")

    # AES-256-GCM reference frames. Wire format: header || nonce64 || ciphertext || tag16.
    # The C backend maps the 8-octet wire nonce to a 12-octet IV: zero32 || nonce64.
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag

    def authenticated_frame(name, key, header_hex, nonce_value, plaintext, expected_ciphertext, expected_tag):
        aad = bytes.fromhex(header_hex)
        wire_nonce = nonce_value.to_bytes(8, "big")
        iv = bytes(4) + wire_nonce
        encrypted = AESGCM(key).encrypt(iv, plaintext, aad)
        check(name + "_ciphertext", encrypted[:-16], expected_ciphertext)
        check(name + "_tag", encrypted[-16:], expected_tag)
        assert AESGCM(key).decrypt(iv, encrypted, aad) == plaintext
        # The 17-octet header is authenticated as AAD.
        changed_header = bytearray(aad)
        changed_header[-1] ^= 1
        for bad_aad, bad_iv, bad_encrypted in (
            (bytes(changed_header), iv, encrypted),
            (aad, bytes(11) + bytes([iv[-1] ^ 1]), encrypted),
            (aad, iv, encrypted[:-1] + bytes([encrypted[-1] ^ 1])),
        ):
            try:
                AESGCM(key).decrypt(bad_iv, bad_encrypted, bad_aad)
            except InvalidTag:
                pass
            else:
                raise AssertionError(name + ": tampered frame accepted")
        print("PASS " + name + "_tamper_rejection")

    authenticated_frame(
        "data_c2s", c2s, "3300000005000000010000000012345678", 1,
        b"hello", "36d84580e1", "3bb1b16b32f7fcb83451f736c68a2609"
    )
    authenticated_frame(
        "ack_c2s", hmac.new(c2s, control_label, hashlib.sha256).digest(),
        "3500000000000000000000000112345678", 2,
        b"", "", "23111c779fe99f554187012835b77030"
    )

    print("Reference vectors PASS; Linux and Zephyr comparison remains pending.")


if __name__ == "__main__":
    main()
