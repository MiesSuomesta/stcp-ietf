# 2026-11-10 uploaded HEAD bundle: UDP reliability comparison

Evidence: user-provided 2026-11-10 18:18:23 ZIP bundles, read directly without rebuilding or modifying source.

## Revisions

- Project: d87cc4cdffa2da285e5c49d7f8fc07a2dfe91d55
- STCP/Linux: 29141c3018a4c8fbb76329f1253f0ea470cdb36c
- SDK/Zephyr: a61335af655c1d4812073648c03f172034659e41
- Raspberry kernel: c1fd977c8366e3353100044544bf75db8179f28d

Revisions above are from the project bundle's `manifest/stcpv7-commits.txt`, not inferred from filenames.

## Direct source findings

| Mechanism | Linux STCP bundle: `kernel/module/rust/src/session.rs` | Zephyr SDK bundle: `Zephyr/common/module/rust/src/session.rs` |
| --- | --- | --- |
| STCP_SEND_WINDOW | 8 (line 148) | **16 (line 165)** |
| STCP_MAX_RETRANSMIT_PER_TICK | 4 (line 151) | 4 (line 167) |
| STCP_MAX_RETRIES | 8 (line 156) | 8 (line 172) |
| Send admission | pending + new frame count <= window (lines 933–935, 970–974) | pending + new frame count <= window (lines 803, 851) |
| Timeout retransmission | bounded retransmission batch, per-frame exponential RTO backoff (lines 1778–1812) | corresponding retransmission loop and per-frame backoff (lines 1541–1571) |

**New interoperability/behavior divergence:** Linux's fixed pending-frame limit is 8, while Zephyr's is 16 in these HEAD bundles. This is not automatically a wire-format incompatibility: the limit is local send-admission policy. It does mean that claiming identical reliability/congestion behavior across platforms would be inaccurate. Do not change either limit without understanding the memory and benchmark consequences.

Neither inspected session path demonstrates a network-responsive congestion window. Further carrier-layer inspection and network-emulated testing are required before claiming safe unrestricted STCP-over-UDP Internet deployment. The earlier 2026-11-10 main-branch audit remains historical; this report supersedes its revision scope.

## Follow-up without production changes

1. Trace the Zephyr and Linux carrier queues and all additional rate-limiting mechanisms.
2. Determine whether the 8-versus-16 difference is intentional platform tuning or an accidental mismatch; test observable behavior under loss and delayed ACK.
3. Preserve both limits in the source review until measured. Do not impose a universal wire-level window of 8 or 16 in the Internet-Draft.
4. Obtain controlled loss, competing-flow, and retransmission logs for a standards-grade UDP congestion algorithm.

No tests were run, and no production source was changed by this comparison.
