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

**Implementation evidence update (2026-11-07):** The implementer reports successful Linux native kernel crypto KATs (6/6), physical Zephyr device PSA AES-GCM KATs (7/7), and a host execution of the original Zephyr Rust KDF (four keys). See `tests/interoperability/linux-zephyr-crypto-kat-2026-11-07.md` for exact evidence and limitations. These results validate the tested operations; they do not establish complete live protocol interoperability or security certification.

The test-only private keys are public and MUST NOT be used for real STCP connections.

Still needed: complete production call-path verification and protocol-level invalid-frame, replay, sequence exhaustion and fail-closed tests, plus fresh Linux–Zephyr LTE interoperability tests. A successful independent Python reference check does not verify the implementation or the complete protocol state machine.

## Implementation comparison checkpoint (2026-11-07)

A read-only inspection of `MiesSuomesta/STCP` branch `main` found:
- `kernel/module/rust/src/frame.rs` declares `STCP_HEADER_LEN = 17`, `STCP_VERSION = 3`, and `STCP_PUBLIC_KEY_LEN = 64`.
- `kernel/module/rust/src/crypto.rs` declares `X25519_KEY_LEN = 32` and `PUBLIC_KEY_WIRE_LEN = 64`.
- `kernel/module/rust/src/session.rs` checks incoming PublicKey frame payloads against `PUBLIC_KEY_WIRE_LEN`.

The existing technical source review describes a 32-byte PublicKey payload, which may reflect a different revision. **Do not conflate a 32-byte X25519 public key with a 64-byte PublicKey frame payload.** Resolve the layout and revision discrepancy by inspecting the active sender/receiver paths on both Linux and Zephyr before adding handshake vectors or normative payload-length claims.

The independently calculated header, KDF, and AES-GCM values were recomputed with Python's cryptography library and matched the existing expected bytes. This does **not** establish that the live Linux or Zephyr code matches the reference. The ACK call in the reference script was inspected and its argument ordering is correct.
