# UDP failed-send retry semantics — HEAD SDK source audit, 2026-11-10

This note checks a specific hypothesis raised by the carrier-error/session audit against the actual uploaded `stcp-project-10.11.2026-181823-SDK.zip`, file `Zephyr/common/module/rust/src/session.rs`. Read-only inspection; no runtime fault-injection test.

## Verified sequence

1. In `send` (approximately lines 817–1009), the UDP reliability path limits the current application send slice to 1024 bytes, checks the pending-frame window, encrypts and constructs a frame.
2. At approximately lines 962–985 it advances `tx_nonce` and `tx_sequence` and enqueues a `PendingFrame` **before** invoking `send_frame` (line ~987). A carrier failure therefore returns an error after the frame has entered the reliability queue. There is no rollback in this branch.
3. On receive, `fill_application_buffer_impl` (approximately lines 1090–1150) authenticates DATA before sequence handling. A frame with `header.sequence < expected` is counted as a duplicate, acknowledged, and not delivered again. A frame above expected is buffered; an in-order frame is processed, then buffered successors are drained.
4. Thus retransmission of the **same queued frame/sequence** is covered by receive-side duplicate suppression. However, if the application retries the same bytes after an initial carrier error, that call may create a **new** frame with a **new sequence number**, which receive-side sequence deduplication cannot identify as an application-level duplicate.
5. This is a *possible ambiguous-commit API outcome*, **not evidence that duplication occurred in an actual test**. Whether a retry is allowed, blocked by pending-window state, or converted to a terminal error depends on timing and socket policy. The C wrapper may return EAGAIN or another errno while the original pending frame remains eligible for retransmission.

## Scope and safe next action

- Do not call the same-sequence UDP retransmission logic broken: it explicitly rejects duplicate DATA sequences.
- Do not promise applications that a failed send means zero bytes were accepted or can never arrive.
- Before modifying source or documenting normative application behavior, run deterministic fault injection on the **first carrier send**, then retry the same payload at the socket API; capture return values, sequence numbers, ACKs, and application-visible delivered bytes.
- Test single-frame and multi-frame calls, blocking/nonblocking modes, and loss/reordering. Establish whether errors after partial application acceptance are reported consistently.
- This issue is distinct from UDP congestion-control readiness and from unauthenticated-key-exchange MITM limitations.

No production code changed and no tests executed.
