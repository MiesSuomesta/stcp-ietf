# Zephyr carrier error to Rust session state — 2026-11-10 HEAD

Read-only audit of user-uploaded SDK ZIP, `Zephyr/common/module/rust/src/session.rs`, `carrier.rs`, and C `stcp_rust_platform.c`. No code changed, no runtime test.

## UDP (reliability-required) send sequence

1. `session.rs` lines 962–985 builds an encrypted frame, reserves pending-frame storage, **advances TX nonce and sequence**, and **enqueues the pending frame before sending**.
2. Line 987 invokes `send_frame`; lines 226–250 call `carrier::transmit`.
3. `carrier.rs` lines 116–140 invokes C `stcp_carrier_send`, maps negative carrier return to `StcpError::Kernel`, rejects zero/overlong sends and enforces full datagram send.
4. `stcp_rust_platform.c` lines 685–705 performs one `zsock_send` per UDP frame, retries EINTR, and reports a short send as EIO.
5. If that initial UDP carrier send fails, `session::send` returns the error **after the frame has already been enqueued**. There is no rollback in the inspected branch.
6. `session::tick` lines 1532–1596 walks pending frames, advances per-frame ages and backoff, and sends at most four due retransmissions per tick. On retry exhaustion it calls `fail_rx_error(ctx, -110)` and returns terminal ETIMEDOUT. A retransmission carrier error returns early from tick; pending state was already updated before that attempt.

**Interpretation:** a transient initial UDP carrier error can coexist with a queued retransmission candidate. This is potentially deliberate reliability behavior, but callers see an error while the frame may later be delivered. Tests must verify application-visible retry semantics and absence of duplicate application payload, rather than assuming a failed send implies no frame was committed.

## Stream carrier contrast

`session.rs` lines 989–1003 advances nonce/sequence before `send_frame`, but does **not** enqueue a pending retransmission frame. C's stream callback loops over partial writes; a later error after partial progress returns a negative errno. The inspected `send` path does not itself roll back the cryptographic sequence on carrier failure. The interaction with connection teardown and frame reassembly requires a focused injected-failure test; this is **not** proof of a live defect.

## Error categories and normative caution

- EAGAIN is not intrinsically a fatal cryptographic/protocol failure; it can indicate transient socket backpressure.
- UDP retry exhaustion explicitly produces terminal ETIMEDOUT in this source.
- A C carrier EIO/EPIPE error is propagated by Rust `transmit`, but **this trace does not establish that every such error immediately transitions the session to terminal state**.
- Do not claim all send failures are fail-closed, or that a failed send guarantees no delivery. Do not specify implementation errno values as wire-level normative behavior.

## Targeted regression tests (not executed)

1. Inject UDP carrier EAGAIN/EIO on first send; inspect pending-frame count, nonce, sequence, retransmission and final application delivery.
2. Repeat with a delayed ACK and a subsequent application retry of the same payload; check whether the application duplicates data.
3. Inject failure during retransmission and verify retry count/backoff, eventual recovery or terminal timeout.
4. Inject partial stream send followed by EPIPE/EIO; inspect receiver frame parsing and local terminal state.
5. Verify blocking and nonblocking socket return values separately from on-wire state.

No production changes. This report records source behavior and test hypotheses, not confirmed protocol defects.
