# STCP wire3 and KDF reference vectors

This directory contains an independently calculated reference test for the **currently documented** STCP wire version 3 header and active Linux X25519/HKDF-SHA256 derivation.

Run from repository root:

    python3 -m pip install cryptography
    python3 tests/vectors/verify_wire3_kdf.py

The script checks:
- a 17-octet header with descriptor 0x33, length 32, sequence 1, acknowledgment 0, connection ID 0x12345678;
- deterministic X25519 public keys and shared secret from public test-only private keys;
- the SHA-256 salt, HKDF extract PRK, client-to-server/server-to-client data keys, and their directional control keys;
- AES-256-GCM DATA and authenticated ACK reference frames, using the complete encoded 17-byte header as AAD and the 12-byte IV formed as four zero bytes followed by the 8-byte wire nonce;
- rejection of modified AAD, nonce/IV, and authentication tag.

**Important:** These are independently generated reference values based on the current draft and technical source review, not yet proven identical to output from the Linux kernel module and Zephyr implementation. Do not call them implementation-verified or interoperable until both implementations are checked against these bytes.

The test-only private keys are public and MUST NOT be used for real STCP connections.

Still needed: comparison against live Linux/Zephyr source and executable tests; protocol-level invalid-frame, replay, sequence exhaustion and fail-closed test cases. A successful independent Python reference check does not verify the implementation or the complete protocol state machine.
