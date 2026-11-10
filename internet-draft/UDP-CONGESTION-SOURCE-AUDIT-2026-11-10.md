# STCP-over-UDP congestion-control source audit — 2026-11-10

Status: read-only Linux source inspection, **not** a new runtime test or a congestion-control design approval.

## Source and revision

Repository: `MiesSuomesta/STCP`, branch `main`, file `kernel/module/rust/src/session.rs`, Git blob `52b5ea23425146e1a8cd874e602eadc092077a1c`. This is the GitHub main snapshot inspected on 2026-11-10; it is not asserted to match the tested 2026-11-07 golden tag or Zephyr firmware.

## Observed mechanisms

| Source location | Observed behavior | What it establishes |
| --- | --- | --- |
| Lines 148–156 | STCP_SEND_WINDOW=8, ACK every 4 frames, maximum 4 retransmissions per tick, 20-ms tick, RTO 20–3000 ms, maximum 8 retries | Static resource/retry limits; **not** a network-responsive congestion window |
| Lines 830–843 | For a carrier requiring STCP reliability, readiness for send requires pending frames plus new frames <= 8 | Bounds unacknowledged frames |
| Lines 878–883 | Sending beyond the fixed pending-frame bound returns Again | Backpressure to application, but not congestion adaptation |
| Lines 1688–1725 | Per-frame timeout, at most 4 retransmits per timer pass, exponential backoff of retransmission timeout up to 3000 ms | Reduces repeated retries for timed-out frames; does not demonstrate adaptation of fresh-data sending rate to congestion |
| Lines 1733–1741 | Exhausting retries transitions to terminal receive error | Failure termination, not congestion avoidance |

The inspected paths contain no demonstrated congestion window that decreases on congestion indications, no documented pacing of new transmissions, and no explicit shared path-capacity estimator. This is a **limited source-backed finding**, not proof that no other layer implements such behavior. The TCP carrier has its own TCP congestion control and is outside this UDP-specific gap.

## Standards Track implication

A fixed eight-frame flight limit plus exponential retransmission backoff is not sufficient evidence of safe UDP congestion response for arbitrary Internet paths. Do not silently equate bounded retransmission with complete congestion control, and do not introduce a new wire algorithm in the RFC without implementation and interoperability evidence.

## Next checks

1. Inspect the exact Linux and Zephyr golden-tag sources, including carrier send queues and any rate limiting outside session.rs.
2. Confirm whether application new-data sending is paced or throttled on loss, rising RTT, persistent ACK delay and ECN (if applicable).
3. Establish minimum datagram sizes, maximum bursts and fairness behavior under loss/competition, using a controlled network emulator and recorded revisions.
4. Only then specify and test an interoperable congestion response for UDP carriage. Until then retain the draft's explicit UDP deployment limitation.

No STCP production code was modified by this audit.
