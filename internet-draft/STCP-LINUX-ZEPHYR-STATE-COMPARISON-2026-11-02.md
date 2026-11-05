# Linux and Zephyr STCP state-machine comparison — 2026-11-02 source bundles

Status: source inspection only; no runtime reproduction of the differences below. No implementation changes.

## Exact source provenance

- Linux: `stcp-project-02.11.2026-183721-STCP.zip`, `kernel/module/rust/src/session.rs`.
- Zephyr common module: `stcp-project-02.11.2026-183721-SDK.zip`, `Zephyr/common/module/rust/src/session.rs`.
- The separately supplied `zephyr-ethernet.zip` contains Zephyr Ethernet driver source (e.g. W5500), **not** the STCP session state machine. The Zephyr STCP Rust implementation is in the SDK archive.

## Verified shared behavior

| Behavior | Linux source | Zephyr source | Assessment |
| --- | --- | --- | --- |
| PublicKey payload exact length | session.rs:613-619 | session.rs:551-559 | Both check `PUBLIC_KEY_WIRE_LEN` |
| PublicKey allowed flags | session.rs:615 | session.rs:552 | Both restrict to `FLAG_COMPRESSION_CAPABLE` |
| HandshakeDone empty payload | session.rs:621-623 | session.rs:561 | Both reject nonempty payload |
| Derive keys after peer PublicKey | session.rs:632-657 | session.rs:564-583 | Both derive keys and send HandshakeDone |
| Ready condition | session.rs:679-682 | session.rs:606-610 | Both require crypto ready **and** peer HandshakeDone |
| Local shutdown | session.rs:2064-2093 | session.rs:1721-1750 | Both set Closed, attempt authenticated Close, close shared endpoint |
| Final release | session.rs:2104-2128 | session.rs:1764-1787 | Both perform local teardown without sending Close |

## Important parser divergence: handshake-to-DATA boundary

**Linux** `process_handshake_frames_locked` (lines 596-694) checks before consuming another frame whether the necessary handshake inputs are present: received or previously stored HandshakeDone, and received key or ready crypto. It then breaks out of the parser loop, leaving subsequent DATA for the established-session receive path. A source comment explicitly documents the HandshakeDone-before-PublicKey case and the early-DATA race.

**Zephyr** `process_handshake_frames` (lines 545-621) loops on `extract_next_wire_frame` until the queue is empty. The match accepts only PublicKey and HandshakeDone; all other packet types return `StcpError::Protocol` (line 562). Its Ready predicate matches Linux, but the parser does **not** contain the Linux pre-consumption boundary check.

**Risk hypothesis, not proven defect:** if a DATA frame is already queued after the handshake frames when Zephyr's parser executes, Zephyr may consume it as an invalid handshake packet, whereas Linux leaves it for the established-session parser. The exact timing, carrier receive scheduling, and observed error path require a targeted test before calling this a confirmed interoperability failure.

## Additional observation

The Linux handshake parser's boundary check includes the persisted `inner.peer_handshake_done` value (lines 604-607), while the Zephyr parser's loop has no equivalent early exit. Both eventually persist received HandshakeDone and require it to enter Ready.

## Proposed non-invasive test cases

1. Peer PublicKey + HandshakeDone + immediate DATA in one TCP receive batch.
2. HandshakeDone before PublicKey, then immediate DATA.
3. PublicKey and HandshakeDone split across TCP reads, followed immediately by DATA.
4. Verify exact delivered application payload and absence of `Protocol` error on Linux and Zephyr separately.
5. Repeat on UDP only after confirming its datagram framing rules; do not assume the same batching semantics.

Each test should record: build revision, carrier, device, wire capture or deterministic frame bytes, frame order, connection state and terminal error.

## Standards implications

- A prospective normative rule that a receiver **MUST NOT** interpret established-session DATA as a handshake frame is a reasonable interoperability candidate, but needs agreement and tests before adoption.
- Do not standardize Linux internal parser loop structure; specify observable protocol behavior instead.
- Preserve the distinction between verified source behavior, inferred risk and actual measured test outcome.
- This comparison does not establish full Linux–Zephyr interoperability, UDP congestion safety, peer authentication or reconnect correctness.

## Follow-up

Confirm the suspected boundary divergence with a test that does not modify the production kernel or Zephyr implementation. If confirmed, treat it as an implementation issue for separate engineering review, not a reason to silently weaken the draft.


## Update — 2026-11-05 source snapshot (supersedes the boundary-divergence hypothesis for current code)

The 2026-11-02 findings above are retained as a historical source-snapshot analysis. New developer-provided archives `stcp-project-05.11.2026-080435-STCP.zip` and `stcp-project-05.11.2026-080435-SDK.zip` contain the current Linux and Zephyr `session.rs` implementations. **Both now include a pre-extraction `have_handshake_inputs` boundary check**, so the previously observed missing Zephyr guard is no longer present in this snapshot.

The current `tests/test_handshake_boundary.py` was executed against the extracted Linux and Zephyr sources on 2026-11-05: **5 tests passed**, including the source-contract check. These are deterministic model/source tests, **not live wire integration tests**.

Added `tests/stcp_first_data_live.py` to exercise immediate first application DATA over real Linux AF_STCP TCP-carried sockets, with a separate server and client, configurable iteration count, and exact payload checks. This is an **additional live smoke regression**, not a controlled HB-01/HB-02 same-receive-queue fixture. An attempted run in the analysis environment could not start because AF_STCP is unavailable there (Linux errno 97); therefore **no live PASS is claimed**.

The HB-01/HB-02 deterministic wire-injection tests on actual Linux and Zephyr endpoints remain **NOT RUN**. Do not infer that TCP send batching forces receiver queue batching. The absence of peer identity authentication remains an intentional, already documented base-protocol property and is not a proposed change.
