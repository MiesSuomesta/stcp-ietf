# Zephyr socket send commit boundary and partial-progress test plan — 2026-11-10 HEAD

Evidence: directly read the uploaded SDK ZIP at `Zephyr/common/module/rust/src/session.rs` and `Zephyr/common/module/src/stcp_socket_offload.c`. No tests were run and no production code changed.

## Exact source behavior

- `session::send` truncates UDP application input to **at most 1024 bytes per call** before framing. This is intentional send-acceptance behavior: a successful return is the accepted byte count, not necessarily the original requested length.
- The loop at approximately lines 860–1008 can create **multiple STCP frames** from the accepted slice, depending on `frame_payload_len(ctx)`. Each frame increments nonce/sequence before its carrier transmission. For reliable UDP, each is also queued for retransmission before its first transmission.
- The local `position` is advanced only after a successful `send_frame`. On a later frame failure, the function returns an error via `?`, rather than returning the count of earlier successfully committed frames.
- `stcp_send_common_locked` in `stcp_socket_offload.c` returns a nonnegative Rust count unchanged. It converts any negative result other than EAGAIN to socket `-1` and `errno=-rc`; blocking EAGAIN is retried, nonblocking EAGAIN returned immediately.
- Therefore a **multi-frame send can have an ambiguous partial-commit boundary**: the caller may observe an error even though earlier frames from that same call have already been sent/queued. Whether the 1024-byte UDP slice spans multiple frames depends on the configured effective frame payload length.
- In the UDP first-frame-error case, the same frame is already queued before the carrier reports failure; the later retransmission can succeed. Sequence-based receive deduplication prevents duplicate delivery of the *same sequence*, not a new application retry assigned a new sequence.
- These are **source-derived possibilities**, not an observed data-duplication bug. Do not claim the full socket API provides all-or-nothing writes or exactly-once application semantics.

## Minimal deterministic regression matrix (proposed, not executed)

| Case | Injected event | Required observations |
| --- | --- | --- |
| U1 | UDP first-frame send returns EAGAIN | Socket return/errno, pending queue, eventual retransmit and delivered bytes |
| U2 | UDP first-frame send returns EIO | Terminal state versus retry state, ACK, duplicate delivery |
| U3 | UDP second frame fails, with payload small enough to fit the 1024-byte call but large enough to span two frames | Socket return, committed first-frame bytes, second-frame retry, final receiver byte stream |
| U4 | Application retries original buffer after U1/U2/U3 | Compare payload and sequence numbers, detect duplicate *application* bytes |
| U5 | Retransmit send fails, then succeeds | Backoff, retries, ACK, queue drain and socket readiness |
| T1 | Stream carrier partially sends a frame then returns EPIPE | Sender error, receiver parser state, teardown, no silent resynchronization |
| T2 | Nonblocking socket encounters full window | EAGAIN, no additional pending frames or nonce advancement |
| T3 | Blocking socket reaches SO_SNDTIMEO | EAGAIN deadline and no infinite wait |

Run with exact HEADs, final build configurations, a deterministic carrier fault hook, packet captures and receiver-side byte counts. A passing general Robot suite is not a substitute for these injected-failure tests.

## Documentation consequence

Do not encode local errno values or 1024-byte send limits as wire-protocol requirements. Keep the Standards Track wire specification separate from socket API semantics; avoid promising no-delivery on error. Do not change the implementation until the test reproduces a user-visible contract violation and an agreed fix preserves Linux/Zephyr interop.
