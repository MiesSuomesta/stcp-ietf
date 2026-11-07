# STCP Linux and Zephyr cryptographic known-answer tests — 2026-11-07

## Scope and provenance

This report records test results supplied by the implementer from executions on the Linux development machine and the physical Zephyr nRF modem on 2026-11-07. The report author did not independently witness the devices or rerun the tests. These are **implementation-specific cryptographic known-answer tests (KATs)**, not full protocol interoperability or security certification.

The tests use the deterministic public test-only vectors documented in `tests/vectors/verify_wire3_kdf.py`. Never use the published private keys in production.

## Test environments

- **Linux:** development host `devaus`, kernel `7.3.0-rc7-next-20261016-nyt-rokkaa`; out-of-tree `stcp_native_kat.ko` compiled from the STCP kernel crypto source plus a test driver, exercising Linux Crypto API.
- **Zephyr:** physical nRF modem running the user's flashed STCP application; `stcp_crypto kat` invokes the device's Zephyr PSA crypto backend. The precise board revision, Zephyr build identifier, and firmware commit were not included in the supplied output.
- **Zephyr KDF:** the original Zephyr Rust KDF source extracted from the 2026-11-07 SDK snapshot and compiled/executed on a Linux host (not executed on the modem).

## Observed results

### Linux native kernel KAT — 6/6 PASS

The implementer supplied the following kernel log:

    STCP KAT PASS Linux kernel KDF C2S/S2C
    STCP KAT PASS Linux kernel AES-GCM DATA
    STCP KAT PASS Linux kernel control KDF C2S/S2C
    STCP KAT PASS Linux kernel AES-GCM ACK
    STCP KAT PASS Linux kernel AES-GCM DATA decrypt
    STCP KAT PASS Linux kernel DATA tampered tag rejected

The test module compiled successfully against the running kernel headers before the results were emitted. The directional control-key derivation was performed by the test driver using kernel HMAC-SHA256 primitives; this does **not** by itself demonstrate that the production Linux control-key path was invoked.

### Zephyr device PSA AES-256-GCM KAT — 7/7 PASS

The implementer supplied the following serial console output:

    stcp> stcp_crypto kat
    STCP KAT PASS Zephyr PSA DATA encrypt
    STCP KAT PASS Zephyr PSA DATA decrypt
    STCP KAT PASS Zephyr PSA tampered tag rejected
    STCP KAT PASS Zephyr PSA tampered AAD rejected
    STCP KAT PASS Zephyr PSA tampered nonce rejected
    STCP KAT PASS Zephyr PSA ACK tag
    STCP KAT PASS Zephyr PSA ACK verify
    STCP KAT PASS 7/7 (device PSA backend)

This confirms the tested PSA backend operations on the device. It does not independently prove that all production STCP send/receive call paths, key lifetimes, replay defenses, or state-machine transitions were exercised.

### Zephyr Rust KDF host execution — PASS

The implementer previously ran a host-native harness using the original Zephyr Rust KDF source extracted from the SDK snapshot. Its reported result was:

    PASS original Zephyr Rust KDF: C2S, S2C, and both control keys

This validates four deterministic derived-key outputs against the shared reference vectors in that host execution. It is not a device KDF execution.

## Interpretation

The observed Linux and Zephyr test runs match the shared reference expectations for the tested KDF and AES-256-GCM DATA/ACK operations. Linux decryption and modified-tag rejection, and Zephyr modified-tag/AAD/nonce rejection, also passed. This is valuable cross-platform cryptographic consistency evidence.

The results do **not** constitute a complete Linux-to-Zephyr live encrypted-frame exchange test. They do not establish exhaustive interoperability, resistance to active man-in-the-middle attacks (STCP deliberately does not authenticate peer identity), full fail-closed behavior, nonce uniqueness over session lifetime, or IETF approval.

## Next protocol-level tests

1. Capture a live Linux–Zephyr LTE handshake and verify that PublicKey (32-byte payload), HandshakeDone, DATA and ACK parsing work with fragmented and coalesced TCP reads, including handshake-to-DATA transitions.
2. Repeat the 2026-11-01 BEN2 STCP-over-TCP upload/download/full-duplex cases with matching firmware and server revisions, and preserve both client and server logs.
3. Reproduce the historical STCP-over-UDP download and full-duplex failures. Capture both endpoints and determine whether the fault is datagram framing, retransmission/ACK processing, buffering, or a different issue; do not infer the root cause from the existing logs.
4. Add protocol-negative cases for truncated/oversized frames, modified authenticated headers, replayed or duplicated packets, sequence/nonce exhaustion, reconnect/reset and fail-closed behavior. Distinguish ordinary packet loss/retransmission from fatal protocol/crypto errors.
5. Record exact Linux and Zephyr commit hashes, firmware version, hardware revision, build flags, test harness versions, timestamps and raw serial/kernel logs for reproducibility.

Related historical LTE evidence: `tests/interoperability/linux-zephyr-lte-2026-11-01.md`.
