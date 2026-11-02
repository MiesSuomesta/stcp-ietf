# Live Linux AF_STCP test

The standalone integration smoke test is `tests/stcp_kernel_loopback.py`.
It is deliberately **not** part of GitHub-hosted CI because GitHub's standard
runner does not have the project's custom AF_STCP kernel module loaded.

## Run on a Linux host with the STCP module loaded

From the `stcp-ietf` repository root:

```sh
git pull --ff-only origin main && python3 tests/stcp_kernel_loopback.py --port 19533
```

The script creates an AF_STCP / SOCK_STREAM / STCP_PROTO_TCP (253)
listener on 127.0.0.1, connects a matching AF_STCP client, transfers
binary payloads in both directions and compares the received bytes.
The script exits nonzero on unsupported sockets, connection errors,
timeouts, unexpected EOF, or corrupted application-visible data.
It does not use a TCP socket as a fallback.

## What PASS means

PASS shows the locally loaded kernel's STCP socket interface successfully
completed this one loopback transfer in both directions. It is not a
cryptographic known-answer test against the kernel's actual encryption
functions, and it does not demonstrate encryption on the wire, peer
authentication, resistance to MITM, UDP behavior, or Zephyr interoperability.

To establish those claims, add a kernel-side deterministic crypto test
hook or KUnit tests that call the actual X25519, KDF and AES-GCM functions,
then compare the resulting bytes with the published vector file. A
packet capture or kernel instrumentation is also needed to establish
the actual encrypted wire representation.

## Evidence recording

Record the UTC date, host kernel version, STCP module version/commit,
exact command, stdout/stderr and exit code. A test should only be
marked PASS after the host executes it successfully.
