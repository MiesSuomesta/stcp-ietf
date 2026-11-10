# Existing UDP reliability test coverage and safe execution plan (HEAD 2026-11-10)

Directly inspected uploaded STCP HEAD ZIP. No live kernel test was run.

## Available harnesses

- `tests/kernel/testing/stcp_udp_reliability_test.c`: loopback AF_STCP/SOCK_STREAM/STCP_PROTO_UDP test on 127.0.0.1:7780, sends a deterministic 256-KiB payload and checks every byte at the receiver; server replies `OK`. This can detect missing, reordered or duplicated **application-visible bytes** during the test.
- `tests/kernel/python/run_stress_suite_udp.sh`: UDP stress runner with a hard-timeout watchdog, process-group cleanup and explicit handling of potentially uninterruptible kernel tasks. Use existing runner rather than ad hoc indefinite waits.
- `tests/soak/example-fault-hooks.sh`: example interface-down/up hook using SSH to a configurable gateway. **Not safe to run without confirming the actual interface and access path**; disabling a remote interface may interrupt management access.
- `kernel/module/src/stcp_module.c`: UDP module fault knobs `drop_first_data`, `duplicate_first_data`, `reorder_first_pair`, `drop_percent`, `delay_first_data_ms`. These are module-level knobs and may affect other sessions.
- `kernel/module/src/stcp_carrier.c`: intentional DATA drop returns a successful length, so it tests packet loss/recovery but **not** negative carrier send errors.

## Recommended controlled order

1. Verify exact Linux kernel/module revision, module load state, no concurrent STCP workloads, and a disposable local test endpoint. Record the original module parameter values before any change.
2. Compile the existing reliability test against the target kernel's STCP API; run **baseline without fault injection** under a hard timeout. Capture return status and receiver byte count.
3. In an isolated test session, run one fault mode at a time: first-DATA drop, first-DATA duplicate, first-pair reorder, bounded delay, then low percentage drop. For each, record socket return, receiver checksum/byte count, retransmission counters, timeout, and full logs. Restore module settings between runs.
4. Only after these pass, extend to controlled RTT/loss and competing-flow tests. Do not infer Internet congestion safety from local loopback recovery.
5. Negative carrier return (EAGAIN/EIO) requires an additional test-only injection or mock; existing drop modes intentionally return success and cannot prove ambiguous-commit behavior.
6. Do not use the example gateway interface-down hook on an unknown remote interface; prefer isolated network namespaces or a lab link where loss of management access is impossible.

## Pass criteria

A passing recovery test must show exact 262144 receiver bytes, correct deterministic contents, expected server acknowledgement, clean termination and no duplicate application delivery. Failure reports must distinguish test harness timeout from protocol retry exhaustion. An injected carrier-error test additionally needs captured caller return/errno, frame sequence, pending queue, and eventual delivery state.

This is an execution plan, **not a test result**. No production code changed.
