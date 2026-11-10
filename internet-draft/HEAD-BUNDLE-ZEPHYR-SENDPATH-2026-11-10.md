# Zephyr active STCP send path — HEAD bundle, 2026-11-10

Source inspection of the user-supplied SDK ZIP at commit `a61335af655c1d4812073648c03f172034659e41`. No build or hardware test was performed.

## Build selection

`Zephyr/common/module/CMakeLists.txt` lines 4–8 compile `stcp_context.c`, `stcp_carrier.c`, and `stcp_socket_offload.c` when `CONFIG_STCP` is enabled. Lines 10–17 add `stcp_rust_platform.c`, buffer pool, Rust RX, and crypto helpers when `CONFIG_STCP_RUST_CORE` is enabled. The file **does not include** `stcp_v2_carrier.c` in its source list. Its line-1 status message still says “STCP2 offload module”, a stale build message rather than evidence of a v2 protocol implementation.

## Socket send call graph

- `stcp_socket_offload.c` lines 790–802: `stcp_sendto` dispatches to `stcp_send_common` when `CONFIG_STCP_RUST_CORE` is enabled; otherwise it directly calls `zsock_sendto` or `zsock_send` on the carrier socket.
- `stcp_socket_offload.c` lines 269–309: Rust-enabled `stcp_send_common_locked` calls `stcp_rust_send`; `-EAGAIN` is retried for blocking sockets, respecting deadline and closing state, while nonblocking sockets propagate `EAGAIN`.
- `stcp_rust_platform.c` lines 667–705: Rust carrier callback `stcp_carrier_send` uses one `zsock_send` per UDP frame (`SOCK_DGRAM`), retries only interrupted sends, and returns an error on short send. This preserves datagram atomicity at the send API boundary.
- `stcp_rust_platform.c` lines 707–726: stream carrier sends use a loop to handle partial writes.

## Consequences

The Rust-enabled Zephyr socket API is not a direct UDP pass-through. It invokes STCP Rust framing/session processing, which then calls the carrier send callback. The C socket offload's direct `zsock_sendto` fallback is a **different compile-time configuration**, and must not be confused with the tested Rust path. Neither the UDP atomic-send helper nor the fixed outstanding-frame limit demonstrates adaptive congestion control.

## Open verification

Check the exact ETH and LTE build `.config` outputs to confirm `CONFIG_STCP_RUST_CORE=y` for each tested image. Trace the Rust FFI send path and actual UDP carrier selection in each image. Verify error propagation and UDP datagram boundaries with a packet capture under impairment before making a stronger interoperability claim.

No production changes; no claim of executed tests.
