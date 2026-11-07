# stcp-ietf

STCP (Secure Transport Communication Protocol) — IETF Internet-Draft development.

## Intended standards status

- **Draft identifier:** draft-paxsudos-stcp-00 (planned)
- **Intended status:** Experimental
- **Target RFC maturity:** Experimental RFC
- **Publication:** In preparation; not yet submitted to or approved by the IETF

The intended status is an Experimental RFC goal, not an existing IETF approval. STCP deliberately does not authenticate peer identity in its base X25519 handshake; active man-in-the-middle attacks remain possible. Fatal cryptographic, protocol, or state inconsistencies require fail-closed connection termination, distinct from normal loss and retransmission. The specification must accurately describe the implementation, including security limitations, interoperability and IANA considerations.

See [the technical source review](internet-draft/STCP-IETF-technical-review.md) for implementation findings and remaining work.

