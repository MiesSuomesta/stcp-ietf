# STCP source-contract review — 2026-11-04

## Input snapshot

Developer-supplied bundle timestamp: 2026-11-04 15:16:38 (local).
Inputs: `stcp-project-04.11.2026-151638-STCP.zip`, `stcp-project-04.11.2026-151638-SDK.zip`, and `stcp-project-04.11.2026-151638-ietf.zip`.

This report is based on source inspection and offline Python tests, not on live Zephyr hardware or an independent security audit.

## Test harness fix

`tests/test_handshake_boundary.py` previously failed under unittest discovery because `self.linux` and `self.zephyr` were only assigned by its command-line entry point. The test now accepts `STCP_LINUX_SESSION` and `STCP_ZEPHYR_SESSION` environment variables and retains the explicit `--linux` / `--zephyr` command-line arguments. When source paths are absent, only the source-contract test is explicitly skipped; deterministic model tests still execute.

## Results

With `STCP_SOURCE`, `STCP_LINUX_SESSION` and `STCP_ZEPHYR_SESSION` pointing to the extracted snapshot, `python3 -m unittest discover -s tests -p 'test_*.py' -v` completed **21 tests, 21 passed, zero skips** in the isolated review environment.

Without Linux/Zephyr paths, the handshake source-contract test is explicitly skipped; this must not be counted as source verification.

## Handshake boundary inspection

- Linux: `kernel/module/rust/src/session.rs`, `process_handshake_frames_locked`.
- Zephyr: `SDK/Zephyr/common/module/rust/src/session.rs`, `process_handshake_frames` (relative to the developer bundle root: `Zephyr/common/module/rust/src/session.rs`).
- Both implementations check `have_handshake_inputs` before calling `extract_next_wire_frame(ctx,queue)`.
- Both use persisted `peer_handshake_done` and `crypto.ready()` when evaluating the boundary.
- The source-contract assertions pass for both snapshots.

This confirms a **static source contract**, not end-to-end runtime correctness. In particular, no hardware Linux↔Zephyr wire capture was executed, and the snapshot does not establish that every carrier or error path behaves identically.

## Remaining verification

1. Execute Linux↔Zephyr handshake and immediate-DATA cases on actual devices, including both PublicKey/HandshakeDone orders.
2. Compare packet captures, session keys and DATA/control authentication behavior byte-for-byte.
3. Test malformed frames, reconnects, timeouts and counter exhaustion on both stacks.
4. Review UDP congestion control and security limitations before claiming Internet-wide interoperability.

No production kernel, SDK, or Zephyr source was modified by this review.
