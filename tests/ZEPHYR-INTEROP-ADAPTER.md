# Linux–Zephyr STCP interoperability test adapter

This repository contains an **evidence validator and orchestrator**, not a
Zephyr firmware implementation or an assertion that hardware tests have passed.

## Operator contract

Create an executable adapter on the test host that accepts:

    adapter --transport tcp --evidence /tmp/tcp.json
    adapter --transport udp --evidence /tmp/udp.json

The adapter must run a **real** STCP Linux-to-Zephyr session on the connected
hardware, independently verify both payload directions byte-for-byte, and
produce JSON **only after** confirming handshake completion and authenticated
application data. It must exit nonzero on any failure or timeout.

Example of the required evidence **schema** (illustrative only; NOT a test result):

    {
      "transport": "tcp",
      "linux_kernel": "ACTUAL_KERNEL_RELEASE",
      "zephyr_firmware": "ACTUAL_FIRMWARE_BUILD_ID",
      "device_id": "ACTUAL_BOARD_IDENTIFIER",
      "client_to_server_bytes": 1024,
      "server_to_client_bytes": 257,
      "client_to_server_verified": true,
      "server_to_client_verified": true,
      "handshake_completed": true,
      "authenticated_data_verified": true
    }

For UDP, the adapter must additionally check datagram boundaries itself.
The adapter must identify the board/firmware and record test logs separately.
The evidence validator checks the declared fields and hashes the input, but
**cannot independently prove that physical hardware was actually used**.

## Execution

Once the hardware adapter exists and is executable:

    python3 tests/stcp_zephyr_interop_robot.py --runner /absolute/path/to/adapter --transport both --repeat 3 --timeout 120 --report /tmp/stcp-zephyr-interop.json

Integrate with the existing parent robot:

    python3 tests/stcp_test_robot.py --linux-source /srv/stcp-project/STCP --zephyr-session /srv/stcp-project/SDK/Zephyr/common/module/rust/src/session.rs --external-zephyr-command python3 /srv/stcp-project/ietf/tests/stcp_zephyr_interop_robot.py --runner /absolute/path/to/adapter --transport both --repeat 3 --report /tmp/stcp-zephyr-interop.json

**Important:** The parent robot's `--external-zephyr-command` consumes the
remaining command arguments. Put other parent flags **before** that option.
A PASS from the validator is operator-backed evidence, not independent
third-party conformance certification.

## Remaining work

- Implement and validate the board-specific adapter against the existing
  Linux and Zephyr STCP applications.
- Test TCP and UDP independently with byte-for-byte verification.
- Add negative, reconnect, loss/reorder and nonce lifecycle scenarios.
- Save firmware hashes, capture logs and test topology with the evidence.
- Do not modify STCP kernel, SDK or Zephyr production code as part of this
  IETF test-only work.
