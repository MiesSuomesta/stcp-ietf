# STCP state machine: source-backed analysis (2026-11-02 bundle)

Status: implementation analysis for draft preparation; **not yet a normative interoperable state-machine specification**.

## Source snapshot and evidence

Developer-supplied archives: `stcp-project-02.11.2026-183721-STCP.zip` and associated SDK, Zephyr Ethernet, IETF and log archives. This report's line-specific findings are from the Linux kernel module Rust and C files in the STCP archive, not from a new execution of the tests. The earlier developer-reported live C loopback PASS is documented separately.

Primary sources:
- `STCP/kernel/module/rust/src/state.rs`: `SocketState`.
- `STCP/kernel/module/rust/src/session.rs`: `bind`, `listen`, `connect`, `start_handshake`, `progress_handshake`, `process_handshake_frames_locked`, `shutdown`, `release`, `fail_rx_error`.
- `STCP/kernel/module/src/stcp_ops.c`: kernel `connect` and `accept` behavior.

## Implementation state inventory

The Rust `SocketState` enum is `New`, `Bound`, `Listening`, `Handshake`, `Ready`, `Closed`, `Error`. These are **internal implementation states** and not wire-visible numeric states.

| Transition | Source-backed precondition / event | Observed behavior | Scope |
| --- | --- | --- | --- |
| New → Bound | `bind()` called in New | Records local address and port; other states return InvalidState | Rust socket API |
| Bound → Listening | `listen()` called in Bound; registration succeeds | Registers listener and backlog; duplicate local listener address returns AddressInUse | Rust listener registry |
| New or Bound → Handshake | `connect()` called in either state | Records peer, creates connection context, initializes sequence/nonce/reliability fields | Rust connect path |
| Listening → accepted child in Handshake | Incoming accepted connection | TCP accepts underlying carrier first; may use an existing queued Rust child or create an external child. UDP has a separate listener/child path | Linux-specific accept mapping |
| Handshake → Ready | Session keys derived **and** peer HandshakeDone received | Sets Ready; receiving peer key alone is insufficient | Rust handshake parser |
| Active state → Closed | `shutdown()` | Sets Closed; attempts an authenticated Close control frame when a connection exists, then closes shared endpoint | Local shutdown API |
| Any released context → Closed | `release()` | Local teardown; explicitly **does not** send Close or invoke shutdown | Resource release |
| Receive failure → Error | `fail_rx_error()` | Sets Error, preserves first terminal errno, clears pending receive application data and marks peer EOF | Receive-error path |

## Handshake ordering and boundaries

- `start_handshake()` requires internal Handshake state and an attached carrier. It emits local PublicKey and immediately retries parser progress, accounting for already queued peer handshake frames.
- The PublicKey payload is checked for exactly `PUBLIC_KEY_WIRE_LEN` octets; the current draft describes this as 64 octets. Only COMPRESSION_CAPABLE is permitted among the received PublicKey flags.
- HandshakeDone requires an empty payload.
- The parser accepts HandshakeDone before PublicKey and preserves the receipt across parser passes.
- Once both the peer HandshakeDone and peer key/derived crypto are available, the parser stops consuming further frames as handshake input; this prevents early application DATA from being misclassified.
- On receipt of a peer PublicKey, the implementation derives directional keys and sends HandshakeDone.
- Ready requires **both** `inner.crypto.ready()` and `inner.peer_handshake_done`. The source explicitly documents a previous first-DATA race if Ready is set earlier.
- These rules do **not** authenticate peer identity. An active attacker can substitute public keys.

## TCP-specific Linux socket behavior

The C `connect` path:
1. Requires IPv4 `sockaddr_in` with `AF_INET`.
2. Connects the underlying carrier before calling Rust connect.
3. Starts the carrier receiver thread **before** emitting handshake frames.
4. Starts handshake and retransmit work.
5. If already Ready, returns success.
6. For O_NONBLOCK, reports `-EINPROGRESS` until readiness can be observed via polling.
7. Otherwise waits for readiness or carrier error with `STCP_CONNECT_TIMEOUT_MS`; interruption and carrier errors are propagated, timeout shuts down carrier and returns `-ETIMEDOUT`.

The C `accept` path distinguishes TCP and UDP:
- TCP first accepts the actual kernel carrier. It may wait briefly (100 ms in the inspected code) for an in-kernel queued child, otherwise creates an external TCP child from carrier endpoints.
- UDP uses the existing Rust accept queue and interruptible wait. This is not equivalent to TCP's carrier accept operation.
- The 100 ms TCP wait is an implementation race-avoidance detail, **not** a proposed wire-level timeout.

## Close versus release versus failure

`shutdown()`, `release()`, and `fail_rx_error()` are distinct paths and must not be collapsed into a single normative Close transition.

- `shutdown()` attempts a protected Close message but ignores transmission failure; therefore local Closed does not itself prove the peer received Close.
- `release()` intentionally performs local cleanup without sending Close.
- `fail_rx_error()` sets Error and terminal errno; Error must not be equated with a successfully authenticated remote Close.

## What is NOT yet proven

1. Complete UDP state transitions, retry/timeout rules and datagram parsing are not exhaustively verified by the source inspection above.
2. SDK and Zephyr behavior has not yet been compared line-by-line to this Linux state table.
3. Exact peer Close, Reset, retransmission and reconnect behavior has not yet been exhaustively mapped.
4. No claim is made that the Linux internal enum is a portable normative protocol state machine.
5. The inspected code does not establish authenticated peer identity or safe Internet-scale UDP congestion control.

## Proposed draft structure (editorial, not new protocol requirements)

1. **Protocol-visible states**: define a small abstract set such as pre-handshake, handshake-in-progress, established, closing and terminated, explicitly mapping each to implementation evidence.
2. **Client handshake**: trigger, PublicKey emission, key derivation, HandshakeDone receipt and establishment predicate.
3. **Server handshake**: distinguish TCP carrier accept and UDP first-datagram session admission, while keeping the abstract wire state common only where proven.
4. **Malformed handshake handling**: wrong payload sizes, flags, unexpected packet types and errors.
5. **Termination**: distinguish authenticated Close, local API release, carrier EOF, Reset and fatal errors.
6. **Timers and reconnect**: specify only after cross-platform evidence; do not copy Linux API timeouts into the wire standard without a design decision.
7. **Test matrix**: Linux TCP/UDP × Zephyr TCP/UDP, ordered and reversed handshake frames, early DATA, duplicate control, partial TCP frames, truncated UDP datagrams, timeout and reconnect.

## Recommended next verification

- Inspect `stcp_ops.c` accept remainder, Rust UDP listener and receive paths, and Zephyr implementation in the supplied archive before writing a mandatory RFC state diagram.
- Add source-based tests for handshake ordering and first-DATA readiness, without modifying the kernel.
- Record expected and observed results separately for Linux and Zephyr.
- Keep the initial RFCXML's existing implementation observations; promote them to MUST/SHOULD only after agreement on portable behavior.

**No kernel, SDK, or Zephyr source modifications are required by this document.**
