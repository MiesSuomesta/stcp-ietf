# STCP handshake normative clarification worklist — 2026-11-04

Status: **proposed normative decisions for review**, not yet adopted requirements. Source basis: `internet-draft/draft-paxsudos-stcp-00.xml`, `internet-draft/STCP-STATE-MACHINE-SOURCE-REVIEW-2026-11-02.md`, and `internet-draft/PUBLICATION-READINESS-REVIEW-2026-11-02.md`. Do not silently promote observed Linux implementation details to universal requirements.

## Existing documented wire behavior

1. A connection in Handshake sends a PublicKey frame containing a 64-octet payload. Octets 0–31 hold the local X25519 public key; the Linux implementation initializes octets 32–63 to zero.
2. A receiver checks PublicKey length and accepted flags; the current Linux implementation permits COMPRESSION_CAPABLE.
3. Upon receiving the peer PublicKey, the endpoint derives directional traffic keys and sends an empty HandshakeDone.
4. HandshakeDone may arrive before PublicKey. Ready is reached only when traffic keys are derived and the peer HandshakeDone was received.
5. The current base handshake does **not** authenticate peer identity; an active man-in-the-middle remains possible. HandshakeDone does not authenticate the transcript.

## Candidate normative rules requiring implementation verification

The following is **candidate wording**, not a claim that all current implementations comply:

- **HS-1 — PublicKey length:** A receiver **MUST** reject a PublicKey frame whose payload length is not exactly 64 octets.
- **HS-2 — HandshakeDone length:** A receiver **MUST** reject a HandshakeDone frame with a nonempty payload.
- **HS-3 — Readiness:** An endpoint **MUST NOT** deliver protected application DATA as established traffic until its traffic keys are available and it has processed the peer HandshakeDone.
- **HS-4 — Stream framing:** An endpoint **MUST** handle a PublicKey or HandshakeDone split across multiple TCP reads, and **MUST NOT** interpret incomplete frames as complete messages.
- **HS-5 — Security claim:** Implementations **MUST NOT** treat the unauthenticated base key exchange as proof of peer identity.

## Decisions blocked pending code and negative tests

| Question | Why it matters | Evidence needed |
| --- | --- | --- |
| Reserved PublicKey bytes 32–63 | Are nonzero values rejected or ignored? | Linux and Zephyr source inspection plus negative vector |
| Flags on PublicKey and HandshakeDone | Which bits are mandatory, optional or invalid? | Decoder checks and cross-platform malformed-frame tests |
| Duplicate PublicKey | Retransmission, key replacement, replay ambiguity | Both implementations' state transitions |
| Duplicate or early HandshakeDone | Must be deterministic without permitting early DATA | Permutation tests and negative cases |
| DATA before Ready | Explicit error/drop/buffer semantics | Wire-level trace and implementation tests |
| Handshake timeout | Prevent stalled peers consuming resources indefinitely | Carrier-specific timers and observable outcomes |
| Version mismatch / unknown frame type | Specify reject vs close vs reset | Negative vectors on TCP and UDP |
| Connection-ID binding | Prevent cross-connection frame confusion | Source trace and multi-connection tests |
| Reconnect / fresh keys / nonce rollover | GCM nonce uniqueness and key lifetime | End-to-end crypto and reconnect tests |
| Peer authentication | Decide whether to add a mandatory mode or explicitly scope unauthenticated encryption | Threat model and protocol design decision |

## Proposed state-transition specification outline

1. **Start:** establish carrier, allocate connection context, enter Handshake, send PublicKey.
2. **Receive PublicKey:** validate framing/version/flags/key material, derive directional keys, send HandshakeDone.
3. **Receive HandshakeDone:** validate its empty payload and record the event even if the peer PublicKey has not yet arrived.
4. **Enter Ready:** only after key derivation and receipt of peer HandshakeDone; ensure DATA is not consumed by the handshake parser.
5. **Abort:** specify exact handling for malformed, duplicate, unsupported-version, timed-out and prematurely closed handshakes. **Do not assign a normative error action before verifying and deciding it.**

## Recommended next steps

1. Compare the current Linux and Zephyr handshake implementations, especially the ten blocked questions above.
2. Add deterministic handshake permutation and malformed-frame tests, with captures for both carriers where supported.
3. Resolve the protocol decisions and only then move confirmed MUST/SHOULD/MAY language into `draft-paxsudos-stcp-00.xml`.
4. Rerun RFCXML rendering and IETF robot validation; retain logs and report remaining SKIPs.
5. Review peer authentication and UDP congestion safety separately as publication-critical open issues.

This document intentionally makes **no production code changes** and does not claim the protocol is ready for Standards Track publication.
