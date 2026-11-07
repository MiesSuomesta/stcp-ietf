# stcp-ietf

STCP (Secure Transport Communication Protocol) — IETF Internet-Draft development.

## Intended standards status

- **Draft identifier:** draft-paxsudos-stcp-00 (planned)
- **Intended status:** Standards Track
- **Target RFC maturity:** Proposed Standard
- **Publication:** In preparation; not yet submitted to or approved by the IETF

Standards Track (targeting Proposed Standard) is the intended outcome; this is an individual Internet-Draft under preparation, not an IETF-approved RFC. STCP deliberately does not authenticate peer identity in its base X25519 handshake; active man-in-the-middle attacks remain possible. Fatal cryptographic, protocol, or state inconsistencies require fail-closed connection termination, distinct from normal loss and retransmission. The specification must accurately describe the implementation, including security limitations, interoperability and IANA considerations.

See [the technical source review](internet-draft/STCP-IETF-technical-review.md) for implementation findings and remaining work.


## Interoperability evidence

A historical Linux–Zephyr nRF9151 LTE test run (2026-11-01) demonstrated successful STCP-over-TCP upload, download, and full-duplex transfers. STCP-over-UDP upload succeeded, while download and full duplex failed in that run. See [the interoperability report](tests/interoperability/linux-zephyr-lte-2026-11-01.md) for the underlying evidence and limitations.
