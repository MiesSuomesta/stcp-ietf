# STCP HEAD bundle — carrier and congestion evidence, 2026-11-10

This is a source-only continuation of `HEAD-BUNDLE-UDP-COMPARISON-2026-11-10.md`. Inputs are the user-uploaded 2026-11-10 STCP ZIP (not the repository default branch). No new test was executed.

## Inspected source

- `kernel/module/rust/src/carrier.rs` lines 92–98: `reliability_required(carrier)` delegates to `stcp_carrier_needs_reliability` when a carrier exists. This is a carrier-policy decision, **not** a rate or congestion-control algorithm.
- `kernel/module/rust/src/carrier.rs` lines 105–115: `transmit` starts with a bounded internal byte queue when no carrier exists; this bound is a memory/queue limit, not demonstrated network pacing.
- `kernel/module/rust/src/session.rs` lines 922–935 and 970–974: pending-frame admission is bounded by `STCP_SEND_WINDOW=8` when the carrier requires reliability.
- `Zephyr/common/module/rust/src/session.rs` lines 787–803 and 829–851: analogous admission uses `STCP_SEND_WINDOW=16`.
- Both inspected session sources lack a named `cwnd`, token-bucket, pacing, or ECN mechanism. This is only a source-search observation, not proof about C carrier functions, modem queues, kernel TCP, or external traffic shaping.

## What is not yet established

The precise C implementation of `stcp_carrier_needs_reliability`, per-carrier UDP transmit scheduling, lower-layer buffering, and Linux/Zephyr loss feedback have **not** been fully traced in this checkpoint. Therefore it would be incorrect to state that the whole stack has no rate limiting. It is equally incorrect to treat fixed flight size and RTO backoff as sufficient evidence of a standards-grade UDP congestion response.

## Decision for the Internet-Draft

Retain the explicit STCP-over-UDP deployment limitation. Keep the 8/16 send-window distinction implementation-specific; it is not a normative wire parameter. Do not change the memory-sensitive Zephyr value, alter the Linux value, or specify an unimplemented congestion algorithm solely from this review.

Next evidence needed: exact carrier send paths, traffic counters, controlled impairment traces, and both platform builds. No production code changes.
