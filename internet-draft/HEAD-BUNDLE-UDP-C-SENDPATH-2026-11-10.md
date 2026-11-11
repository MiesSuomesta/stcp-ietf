# UDP carrier send-path audit — uploaded HEADs (2026-11-10)

Read-only inspection of the 2026-11-10 user-uploaded STCP and SDK ZIPs. No code changed or tests run.

## Linux: verified C carrier

Source: `STCP/kernel/module/src/stcp_carrier.c` (archive-relative `kernel/module/src/stcp_carrier.c`).

- Lines 910–913: `stcp_carrier_needs_reliability` returns true **only for UDP carriers**. Thus the Rust fixed-flight retransmission path is UDP-specific by this carrier decision.
- Lines 198–240: `stcp_udp_send_one` obtains a short-lived socket send reference, then calls `kernel_sendmsg` directly. There is no visible time-based pacing or network-feedback check in this helper.
- Lines 1124–1138: normal UDP production send path calls `stcp_udp_send_one` immediately after connected/peer checks.
- Lines 1140–1193: separate fault-injection path supports intentional drop, delay, reorder and duplicate DATA frames. This branch runs only when `stcp_test_active()`; it **must not** be interpreted as production congestion control.
- Lines 155–166: socket-buffer tuning uses `STCP_UDP_SOCKET_BUFFER_SIZE` = 16 MiB (line 32). A socket buffer size is not a congestion algorithm.

The Rust session path previously reviewed enforces an 8-frame outstanding limit, ACK/retransmission logic and RTO backoff. Together, these provide bounded flight size and loss recovery but **do not demonstrate adaptive congestion control or pacing** for arbitrary UDP paths. Kernel/IP/qdisc behavior and externally imposed shaping remain outside this source-level conclusion.

## Zephyr: carrier split

- `SDK/Zephyr/common/module/src/stcp_carrier.c` is a small socket wrapper, not the entire send path.
- `SDK/Zephyr/common/module/src/stcp_rust_platform.c` includes `zsock_send` calls around lines 691 and 708.
- `SDK/Zephyr/common/module/src/stcp_socket_offload.c` includes `zsock_sendto`/`zsock_send` around lines 800–801.
- `SDK/Zephyr/common/module/src/stcp_v2_carrier.c` also contains socket sends, but **the presence of a legacy-named file does not establish that it is compiled or used**. Do not make protocol-version claims from filenames alone.

Zephyr's Rust session has a 16-frame fixed window. Further call-graph and build-selection tracing is necessary to establish which Zephyr socket send path is active for each target (ETH/LTE) and whether any lower layer throttles it.

## Standards-track implication

The currently available evidence is insufficient to claim STCP-over-UDP is congestion-safe for unrestricted public Internet deployment. Keep the draft's deployment limitation, and do not prescribe a speculative algorithm. A standards-grade design needs measurable response to congestion signals, coexistence/fairness analysis, explicit requirements and Linux/Zephyr interoperability evidence. Fixed window limits 8/16 are local implementation policies, not wire-format constants.

## Next verification

1. Resolve Zephyr's actual per-target build selection and socket send call graph.
2. Audit kernel carrier transmit/error behavior for loss and `EAGAIN` propagation.
3. Run controlled loss/RTT/reordering/fairness tests on both implementations with the exact uploaded revisions and test configurations.
4. Update normative text only after the implemented behavior is demonstrated.
