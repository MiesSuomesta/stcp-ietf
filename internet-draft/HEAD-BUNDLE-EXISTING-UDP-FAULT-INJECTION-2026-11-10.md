# Existing Linux UDP fault injection: suitability for failed-send tests

Evidence: direct inspection of uploaded 2026-11-10 STCP HEAD ZIP, `kernel/module/src/stcp_module.c` lines 53–139 and `kernel/module/src/stcp_carrier.c` lines 1124–1193. Source-only audit; tests not executed.

## Existing test controls

Module parameters in `stcp_module.c`: `drop_first_data`, `duplicate_first_data`, `reorder_first_pair`, `drop_percent`, `delay_first_data_ms`. Initialization seeds atomic one-shot budgets. The percentage drop uses deterministic modular arithmetic `(sequence * 37) % 100 < percent`.

The UDP send path uses a direct `stcp_udp_send_one` fast path when no fault mode is active. Fault handling applies to DATA frames and includes a mutex and a held-frame buffer for reordering.

## Crucial distinction

- **Intentional drop** (carrier.c 1140–1144) returns `len`, deliberately **pretending successful carrier transmission**. This tests retransmission after network loss, **not** socket-visible EAGAIN/EIO or ambiguous failed-send commit.
- **Intentional delay** sleeps before send, potentially influencing blocking behavior, but does not inject a negative carrier result.
- **Reorder** stores the first DATA frame and reports success; when another DATA frame arrives, sends it and then the held frame.
- **Duplicate** transmits the same DATA frame a second time. If the duplicate transmit fails, the helper may return an error **after the first transmission succeeded** (1186–1189). This is a possible indirect error-after-delivery scenario, but depends on a real lower-level failure and is not a deterministic errno-injection hook.
- **Drop percentage** is reproducible per initialized module sequence, not per-session; avoid assuming independent deterministic schedules when other UDP DATA traffic is active.

## Test strategy without production changes

1. First run existing drop/duplicate/reorder/delay controls to establish baseline retransmission, ACK, duplicate suppression and socket return behavior.
2. For the specific **negative-return-on-first-send** and **negative-return-on-second-frame** cases, these controls are insufficient. A targeted test-only fault hook or isolated unit-level carrier mock would be needed, subject to review. Do not change production code or infer that existing loss tests prove the ambiguous-commit case.
3. Keep the two evidence categories separate in the Standards Track readiness review: packet impairment recovery vs carrier error reporting.
4. Verify test-module parameters are reset after tests; they are module-global and can affect other sessions.

No code modifications, no test execution.
