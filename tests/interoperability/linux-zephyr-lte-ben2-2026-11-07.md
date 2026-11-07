# STCP Linux–Zephyr LTE-M Internet BEN2 full-duplex — 2026-11-07

## Scope

Implementer-provided BEN2 server output for a successful end-to-end test: Zephyr nRF9151 STCP client over LTE-M and public Internet to Linux STCP BEN2 server at lja.fi:19000. Transport was `stcp-tcp` (STCP carried over TCP), BEN2 version 2, mode 3 (full duplex), 4096-byte chunks, 5,242,880 bytes in each direction. This is a reported live protocol test, distinct from cryptographic known-answer tests. The report author did not independently rerun the test.

## Observed server result

    BEN2_RESULT {"timestamp_ms":1794045202674,"sequence":1,"schema":1,"protocol":"BEN2","transport":"stcp-tcp","version":2,"mode":3,"chunk_bytes":4096,"total_bytes":5242880,"status":"PASS","server":{"rx_bytes":5242880,"tx_bytes":5242880,"rx_window_us":237752898,"tx_window_us":374520,"elapsed_us":327272071,"receive_callbacks":5116,"send_callbacks":5120,"rx_mib_s":0.021030,"tx_mib_s":13.350422,"aggregate_mib_s":0.030556},"client":{"carrier":"lte","tx_bytes":5242880,"rx_bytes":5242880,"tx_us":237588440,"rx_us":327149780,"send_calls":5120,"recv_calls":4247,"eagain":0,"errors":0,"stack_used_bytes":2536,"stack_free_bytes":1560,"connect_us":1436188,"elapsed_us":327149841,"tx_mib_s":0.021045,"rx_mib_s":0.015284}}

## Interpretation

- **PASS:** Both Linux and Zephyr BEN2 counters agree on 5 MiB sent and received in each direction, for 10 MiB total application payload.
- Server elapsed time: 327.272 seconds; client elapsed time: 327.150 seconds.
- Client transmit rate: 0.021045 MiB/s; client receive rate: 0.015284 MiB/s. These are measured over distinct per-direction windows; do not mistake server `tx_mib_s=13.350422` (a short send-window rate) for sustained LTE download throughput.
- Client reported zero EAGAIN and zero errors, and stack used/free of 2536/1560 bytes.
- Prior server progress logs reached full 5 MiB RX/TX before the final BEN2_RESULT. This is not proof of a stuck completion handler: the client receive duration was approximately 327 seconds, longer than its send duration of approximately 238 seconds. The eventual PASS establishes successful completion of this run.
- Earlier 5 MiB Ethernet full-duplex result took 97.552 seconds, approximately 3.35 times shorter than this LTE run. These are two runs in different network conditions, not a controlled throughput benchmark.

## Limitations and next steps

This result demonstrates the tested STCP/TCP LTE-M Internet path with the specified binaries and BEN2 harness. It does not prove STCP-over-UDP interoperability, complete conformance, cryptographic peer authentication, or exhaustive fault handling. The exact implementation commits, firmware image hashes, and raw modem serial logs were not provided with this result.

Next: separately test STCP-over-UDP upload/download/full duplex at small sizes, preserve both endpoint logs, and diagnose the historically failing UDP download/full-duplex paths before increasing load. Also test handshake/data boundary and fatal-error behavior.
