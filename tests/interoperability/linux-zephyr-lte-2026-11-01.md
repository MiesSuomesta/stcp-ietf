# STCP Linux–Zephyr LTE Interoperability Test Report

## Identification

- Test date: 2026-11-01
- Test run: 20261101T125233Z-185065
- Zephyr client: nRF9151, LTE
- Peer: Linux BEN2 STCP benchmark server
- Endpoint: lja.fi:19000
- BEN2 request version: 2
- Requested transfer: 3,000 bytes per direction; chunk size 2,048 bytes

## Results

| Carrier | Mode | Zephyr TX (B) | Zephyr RX (B) | Linux RX (B) | Linux TX (B) | Server result |
|---|---|---:|---:|---:|---:|---|
| STCP over TCP | Upload | 3000 | 0 | 3000 | 0 | PASS |
| STCP over TCP | Download | 0 | 3000 | 0 | 3000 | PASS |
| STCP over TCP | Full duplex | 3000 | 3000 | 3000 | 3000 | PASS |
| STCP over UDP | Upload | 3000 | 0 | 3000 | 0 | PASS |
| STCP over UDP | Download | 0 | 0 | 0 | 3000 | FAIL |
| STCP over UDP | Full duplex | 3000 | 0 | Not confirmed | Not confirmed | No final server result in reviewed log |

The Zephyr serial results reported status 0 for all three STCP-over-TCP cases and STCP-over-UDP upload. The test runner also recorded PASS for those four cases. The Linux server emitted BEN2_RESULT records with status PASS and matching byte counters.

The Zephyr client reported status -105 for STCP-over-UDP download and full duplex. For download, the server reported transmitting 3,000 bytes but did not receive a completed client result; it subsequently reported a timeout (OS error 110). For full duplex, the reviewed server log shows acceptance of the request but no final BEN2_RESULT.

## STCP-over-TCP details

| Direction | Zephyr elapsed (ms) | Server result | Client errors reported by server |
|---|---:|---|---:|
| Upload | 316 | PASS | 0 |
| Download | 803 | PASS | 0 |
| Full duplex | 572 | PASS | 0 |

The reported durations are Zephyr benchmark elapsed values, not a normalized end-to-end throughput comparison. The server's own elapsed and transfer-window timings differ.

## Evidence provenance

The original artifacts reside in the separate STCP implementation project, not in this repository:

    utilities/zephyr-matrix-results/lte/20261101T125233Z-185065/

Files reviewed:

- run.log — runner PASS records and Zephyr serial result summaries
- serial.log — Zephyr benchmark output
- stcp-tcp-UL.log, stcp-tcp-DL.log, stcp-tcp-FULL.log — per-direction Zephyr logs
- stcp-tcp-server.log — three Linux BEN2_RESULT PASS records
- stcp-udp-server.log — upload PASS, download FAIL/timeout, and incomplete full-duplex trace

The benchmark.json matrix summaries previously inspected showed NOT RUN entries inconsistent with execution evidence. This report therefore uses the actual serial, runner, and server records rather than treating that matrix summary as authoritative.

## Interpretation and limitations

This historical run demonstrates successful application-data exchange between the tested Zephyr and Linux implementations over LTE using STCP carried over TCP, including bidirectional transfer. It also demonstrates STCP-over-UDP upload in this configuration. It does not demonstrate successful STCP-over-UDP download or full duplex.

The server's PASS results and matching counters establish successful completion under the BEN2 test harness. This report does not independently audit the BEN2 payload-verification implementation or establish exhaustive protocol conformance.

This run alone does not prove interoperability across other STCP versions, networks, platforms, or implementations. It does not validate cryptographic security against active attackers, and STCP's unauthenticated key exchange does not authenticate peer identity.

No new tests were executed in preparing this report.
