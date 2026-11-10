# Zephyr Rust–C socket error propagation — 2026-11-10 HEAD

Read-only inspection of the user-provided SDK HEAD ZIP, specifically `Zephyr/common/module/src/stcp_socket_offload.c` and `Zephyr/common/module/src/stcp_rust_platform.c`. This is source evidence, **not** an executed test or a complete Rust call-graph audit.

## Application socket API

- `stcp_socket_offload.c` `stcp_send_common_locked`: when `CONFIG_STCP_RUST_CORE` is enabled, calls `stcp_rust_send`. Non-`-EAGAIN` negative returns become `errno=-rc` and socket return `-1`. `-EAGAIN` is immediately returned for nonblocking sends; blocking sends wait for a wakeup in at most 10-ms slices, subject to deadline.
- A blocking send reaching its configured deadline also returns **EAGAIN**, not ETIMEDOUT. The draft and tests should not claim otherwise for this socket API.
- `ctx->closing` returns **EBADF**; `ctx->write_shutdown` returns **EPIPE** before invoking Rust. These are local socket-state decisions, not evidence of on-wire close frames.
- `stcp_send_common` takes `tx_lock` without waiting initially, then waits in 1-ms slices for blocking callers. Nonblocking/deadline expiry returns EAGAIN. This lock contention is a separate cause of EAGAIN from Rust send-window exhaustion.
- `stcp_recv_common_locked`: `read_shutdown` yields 0 (EOF), negative Rust errors other than EAGAIN map to errno, and nonblocking or deadline-expired receive returns EAGAIN. A blocking receive waits in up-to-100-ms slices.
- The observed code uses `stcp_wait_io` for blocking waits. Whether all close/error paths wake waiters promptly needs an event and teardown trace; not established by this review.

## Underlying carrier callback

- `stcp_rust_platform.c` `stcp_carrier_send`: UDP uses exactly one `zsock_send` per frame, retrying EINTR, mapping carrier error to negative errno, and returning EIO for short UDP sends.
- Stream carrier loops over partial writes; `zsock_send` returning zero becomes EPIPE, and negative non-EINTR returns negative errno. **Partial stream progress before a subsequent error** is not reported as a successful byte count by this callback; the caller sees the final error. This deserves a targeted transport-failure test, not an immediate source change.
- These are callback return values; the full propagation through Rust session state and retransmission is **not yet verified**.

## Recommended focused tests (not executed)

1. Nonblocking send with a full STCP window and with tx_lock contention: confirm EAGAIN and no silent data duplication.
2. Blocking send with finite SO_SNDTIMEO: confirm deadline behavior (EAGAIN), wakeup after ACK, and shutdown races.
3. Carrier-injected UDP EAGAIN/EIO and short-send: verify error propagation, session consistency and fail-closed handling where fatal.
4. Stream partial write followed by EPIPE/EIO: verify whether a frame is retried or session terminated without wire corruption.
5. Blocking recv timeout, read shutdown, close while waiting: verify EAGAIN/EOF/EBADF and no stuck waiter.

Do not equate ordinary EAGAIN with a fatal cryptographic/protocol failure. Do not alter production code before reproducing a defect and confirming desired semantics.
