# Verified commit-before-send sequence in both HEAD bundles

Date: 2026-11-10. Direct read of user-uploaded `stcp-project-10.11.2026-181823-STCP.zip`, not inferred from earlier audit notes. No production change and no executed test.

## Source anchors

| Stage | Linux `kernel/module/rust/src/session.rs` | Zephyr `Zephyr/common/module/rust/src/session.rs` |
| --- | --- | --- |
| Reliable branch | 1122–1148 | 962–987 |
| Reserve pending-frame storage | 1133 | 973 |
| Advance TX nonce and sequence | 1134–1135 | 974–975 |
| Push pending frame | 1137–1144 | 977–984 |
| First carrier send, may error | 1148 | 987 |
| Nonreliable branch advances nonce/sequence before send | 1159–1164 | 998–1003 |
| Advance accepted input position after successful send | 1166 | 1005 |
| Return full input length on success | 1169 | 1008 |

Both implementations commit nonce and sequence before calling the carrier for **both** reliable and nonreliable sends. Only reliable sends enqueue the exact encrypted frame for retransmission. A failed carrier send after the reliable commit therefore leaves a pending frame in the queue in these code paths; the application-facing error does not mean the frame is uncommitted.

The same commit-before-send ordering appears on both platforms, so this is **not** by itself a Linux/Zephyr wire incompatibility. Differences in the surrounding socket wrapper and timeout errno remain separate concerns. A receiver's sequence deduplication addresses replay of the same frame, not a fresh application retry with a new sequence.

## Reproduction gate

A production fix should not be selected from this static observation alone. The minimal deterministic experiment is to inject a carrier failure at the **first send of a queued UDP DATA frame**, observe the socket result, advance the retransmission timer, record any successful retransmission and ACK, then retry the application buffer and compare receiver-visible bytes. Repeat with a failure at the second frame of one Rust call. Record final frame payload size, sequence, nonce, carrier, socket mode and both commit hashes.

No protocol or production code modified. This is a precise evidence anchor for the proposed tests and for avoiding an unsupported all-or-nothing socket guarantee.
