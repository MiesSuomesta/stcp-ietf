# Zephyr–Raspberry Pi STCP hardware regression evidence — 2026-11-04

Status: developer-provided live serial output; recorded for IETF engineering evidence. This is not an independent audit or IETF interoperability certification.

## Test setup

- Zephyr STCP socket-echo robot, built with `STCP_SDK_ECHO_ROBOT=1`.
- Raspberry Pi STCP echo server deployed over SSH as `pi@raspi`, bound to `0.0.0.0:19000`.
- Standard Make workflow deploys/starts the Pi echo server, builds Zephyr firmware and flashes the device.
- Robot opens a fresh STCP socket for each case, exchanges byte-for-byte echo payloads, and configures both `SO_RCVTIMEO` and `SO_SNDTIMEO` to 30 seconds.
- Developer reported the following serial output after the run:

```text
SDK_ROBOT PASS suite=stress-sequential connection=200 tx=256 rx=256
SDK_ROBOT PROGRESS 785/785 100% suite=stress-sequential elapsed=802s eta=0s
SDK_ROBOT SKIP suite=stress-parallel reason=not_implemented
SDK_ROBOT SKIP suite=udp-smoke reason=not_implemented
SDK_ROBOT SKIP suite=udp-matrix reason=not_implemented
SDK_ROBOT SUMMARY status=PASS passed=785 failed=0
```

## Result and scope

- **PASS: 785 / 785 executed cases**; **FAIL: 0**; duration **802 seconds**.
- Suites represented by the executed cases: payload matrix, lifecycle, and sequential stress.
- **Three suites skipped**: stress-parallel, udp-smoke, udp-matrix. These are *suites*, not three failed test cases.
- The successful run confirms the exercised Zephyr-to-Pi TCP-carried STCP echo path, including successful `SO_SNDTIMEO` configuration in the robot connection setup.
- It **does not** demonstrate that a blocked send expires at the configured deadline; a dedicated backpressure/timeout test remains necessary.
- It does **not** establish UDP operation, congestion safety, parallel connection behavior, authenticated peer identity, full cryptographic interoperability vectors, or cross-platform wire compatibility for every error and reconnect case.
- Reported pool snapshot during the run: `frame=0/16 large=0/2 peak=4/1 failures=0`; heap snapshot `used=0 free=32680 peak=1184`. These are point-in-time diagnostics, not a memory-leak proof.
- Repeated diagnostic lines appeared at Zephyr error log level despite zero reported pool failures; diagnostic log-level/duplication cleanup is separate from protocol conformance.

## Relation to the IETF robot report

The separately committed `tests/robot-report-20261104.json` reports **113 PASS, 0 FAIL, 1 SKIP** for a different IETF validation suite. These counts must **not** be added together or presented as a single homogeneous test suite.

## Evidence limitations / reproducibility follow-up

- Preserve complete timestamped serial logs, Zephyr and Pi commit SHAs, firmware build configuration, Pi server binary hash, and network captures for independently reproducible evidence.
- Capture handshake, encrypted DATA, and control frames on the carrier and compare them to the draft's wire and cryptographic vectors.
- Run negative tests for malformed handshake messages, retransmission, reconnect, nonce/key lifetime, and a genuinely blocked `SO_SNDTIMEO`.
- This record is based on the developer's console excerpt and discussion; the complete raw serial log and precise tested commit SHAs were not provided here.
