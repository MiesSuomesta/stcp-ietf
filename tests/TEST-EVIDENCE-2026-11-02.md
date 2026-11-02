# STCP interoperability test evidence

## Scope and status

This report records a user-reported execution of the independent Python
known-answer tests, together with the repository's reproducible test procedure.
It does **not** establish Linux kernel / Zephyr implementation interoperability,
a complete STCP handshake, resistance to active man-in-the-middle attacks,
or IETF approval.

- **Repository:** MiesSuomesta/stcp-ietf
- **Test source:** tests/test_stcp_vectors.py
- **Vector specification:** internet-draft/STCP-interoperability-vectors-01.md
- **Evidence:** commit edd595f1c48c970cff075ac1fca7bb45be4e1e23
- **Reported execution:** 2026-11-02, development machine (devaus)
- **Reported Python:** 3.13
- **Reported cryptography package:** 49.0.0
- **Result:** 5 tests passed, 0 failed, 0 errors, 0.011 s (as recorded in the commit message)
- **Evidence type:** developer-run console output, recorded in a Git commit message;
  no signed CI artifact or independent device capture is attached.

## Reproduce

From the repository root, in an environment with Python 3.13:

1. Install the dependency: `python3 -m pip install 'cryptography>=46,<50'`
2. Run the suite: `python3 -m unittest discover -s tests -p 'test_stcp_vectors.py' -v`

The tests use fixed, publicly disclosed X25519 test private keys only.
Do not use these keys in production.

## Test coverage

| Test | What it checks | Reported |
| --- | --- | --- |
| test_x25519_and_kdf | Public keys, shared secret, salt, PRK, directional and control keys against fixed expected bytes | PASS |
| test_data_frame | Deterministic AES-256-GCM DATA frame bytes and successful decryption | PASS |
| test_ack_frame | Deterministic authenticated ACK bytes and verification | PASS |
| test_header_flags_and_endianness | Version/type/flags encoding and big-endian header fields | PASS |
| test_aead_tampering_rejected | GCM rejection when an authenticated header byte or ciphertext/tag byte changes | PASS |

These tests calculate values using Python's `cryptography` library and
Python standard-library hashes/HMAC. They compare against fixed values
previously derived from the documented wire format and key schedule.
They do **not** invoke the actual STCP kernel module, its C/Rust crypto
implementation, or a Zephyr firmware build. Thus they verify the test
implementation and published vectors, not cross-implementation agreement.

## Automated checks

The GitHub Actions workflow `.github/workflows/ietf-checks.yml` runs:

- The same five Python known-answer tests on Python 3.13.
- An XML parser check and an `xml2rfc` text-rendering check for
  `internet-draft/draft-paxsudos-stcp-00.xml`.

**CI result:** not independently confirmed in this report. Inspect the
repository's Actions page for the result of each workflow run. A passing
RFCXML job demonstrates tool acceptance/rendering, not IETF publication.

## Remaining evidence needed for interoperability claims

1. Run the vectors against the STCP Linux implementation's actual
   X25519/KDF/AES-GCM paths; record source revision and exact outputs.
2. Run the same cases against the Zephyr implementation and compare
   byte-for-byte, including both traffic directions.
3. Capture and validate a complete TCP-carried and UDP-carried session,
   including handshake, encrypted DATA, authenticated ACK/control frames,
   close/reconnect, and malformed-frame rejection.
4. Record test hardware, firmware/kernel revisions, transport settings,
   commands, raw logs, pass/fail criteria and reproducible artifacts.
5. Document unresolved handshake authentication and UDP congestion-control
   issues before making stronger security or standards-readiness claims.

## Provenance

The latest reported 5/5 PASS was preserved as the **commit message** of
[edd595f](https://github.com/MiesSuomesta/stcp-ietf/commit/edd595f1c48c970cff075ac1fca7bb45be4e1e23).
The file change in that commit is only a blank line in README.md; this
report provides a discoverable evidence record without claiming the
commit added an executable test log.


## Live Linux kernel integration test — developer-reported PASS

On 2026-11-02 the developer compiled and ran the standalone C test
`tests/stcp_kernel_loopback.c` from commit
`7e51b73ef0c91560655aa6168ca8215ebb3a6a01`
on the `devaus` host, with the STCP module installed and loaded.
The host kernel identified in the session was
`7.3.0-rc7-next-20261016-nyt-rokkaa`.

Command:

    cd /srv/stcp-project/ietf && git pull --ff-only origin main && gcc -O2 -Wall -Wextra -pthread -o /tmp/stcp-ietf-loopback tests/stcp_kernel_loopback.c && timeout 45s /tmp/stcp-ietf-loopback 19533

Observed output:

    PASS: AF_STCP TCP loopback, client->server=1024 bytes, server->client=257 bytes
    LIMITATION: no wire capture, crypto known-answer comparison, or Zephyr interoperability.

The test uses blocking AF_STCP / SOCK_STREAM / STCP_PROTO_TCP
sockets with IPv4 sockaddr_in on loopback. It compares deterministic
binary data transferred in both directions. This is a live
implementation-backed socket transport test, unlike the independent
Python known-answer tests and static source-contract tests.

**Evidence boundary:** This result comes from developer-supplied console
output; it has not been independently reproduced or accompanied by
a packet capture. It does not prove byte-for-byte agreement of the
kernel's crypto functions with the published vectors, cryptographic
peer authentication, UDP operation, or Linux/Zephyr interoperability.
The kernel was not changed for this test.
