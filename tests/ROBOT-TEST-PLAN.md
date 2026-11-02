# STCP IETF test robot

Entry point: `python3 tests/stcp_test_robot.py`.

This robot runs independently of production STCP code and writes a structured JSON evidence report. It does **not** patch, rebuild, reload, or reconfigure the STCP kernel, SDK, or Zephyr firmware. A zero exit status means **no executed checks failed**, not that skipped hardware tests passed.

## Test categories

| Check | Default | Meaning |
| --- | --- | --- |
| Python crypto known-answer vectors | RUN | Independent Python crypto vectors; not kernel crypto |
| RFCXML v3 XML parse | RUN | Syntax and version |
| RFCXML text/HTML rendering | RUN if xml2rfc installed | Draft rendering |
| Linux source contract | RUN when --linux-source supplied | Static implementation checks |
| Linux/Zephyr handshake boundary | RUN when both source paths supplied | Static contract + deterministic model; not live interoperability |
| Live Linux AF_STCP TCP loopback | SKIP unless --live-linux | Actual kernel module, bidirectional fixed binary payload |
| External Zephyr integration | SKIP unless --external-zephyr-command supplied | Runs operator-provided executable; operator must ensure it actually tests a Zephyr device |

## Developer machine

From the IETF repository root:

    python3 tests/stcp_test_robot.py --linux-source /srv/stcp-project/STCP --zephyr-session /srv/stcp-project/SDK/Zephyr/common/module/rust/src/session.rs --report /tmp/stcp-robot-offline.json

For **100 real Linux TCP loopback runs** on a host with a working loaded AF_STCP module and a free test port:

    python3 tests/stcp_test_robot.py --linux-source /srv/stcp-project/STCP --zephyr-session /srv/stcp-project/SDK/Zephyr/common/module/rust/src/session.rs --live-linux --live-repeat 100 --live-port 19533 --timeout 45 --report /tmp/stcp-robot-live.json

**Caution:** live tests bind a local port, open kernel sockets, and send data. Run on the development host, not production. The test stops at the first failing live iteration and returns nonzero. Repeated runs use the same port, so a bind failure can reflect port reuse/cleanup and must be investigated.

An optional `--external-zephyr-command COMMAND [ARGS ...]` invokes an **existing** real hardware interoperability runner. This repository does not currently provide one. The robot cannot infer that a command truly talks to Zephyr; include actual device identity, firmware revision, transport, packet captures and runner logs before making interoperability claims.

## Reports and CI

Each test records PASS/FAIL/SKIP, category, elapsed seconds and a bounded combined stdout/stderr excerpt in JSON. A FAIL makes the robot exit with status 1. A SKIP is never counted as PASS. The CI workflow runs the offline subset and uploads the JSON artifact; CI cannot exercise a local kernel module or Zephyr board.

Do not commit reports containing private addresses, keys, device identifiers or secrets. Published vectors use nonproduction test keys.

## Limitations and next tests

The current live C loopback sends 1024 bytes in one direction and 257 in the other. It does **not** inject crafted handshake packets, force handshake frame coalescing, exercise UDP, prove crypto known-answer equivalence in the kernel, or establish Linux/Zephyr interop. Those require additional real runners, hardware setup and reproducible packet-level evidence.

The source/model test confirms a parser boundary divergence; it does **not** demonstrate that a production Zephyr session fails on the wire. Do not silently turn a hypothesis into a confirmed defect.

No implementation changes are part of this robot.
