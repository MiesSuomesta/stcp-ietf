# STCP handshake normative clarification worklist — 2026-11-04

Status: **proposed normative decisions for review**, not yet adopted requirements. **Design decision confirmed 2026-11-04: the base STCP protocol does not and will not authenticate peer identity.** Source basis: `internet-draft/draft-paxsudos-stcp-00.xml`, `internet-draft/STCP-STATE-MACHINE-SOURCE-REVIEW-2026-11-02.md`, and `internet-draft/PUBLICATION-READINESS-REVIEW-2026-11-02.md`. Do not silently promote observed Linux implementation details to universal requirements.

## Draft integration update — 2026-11-10

The current draft now contains a dedicated Handshake Wire Requirements section specifying exact 32-octet PublicKey payloads, empty HandshakeDone payloads, Ready gating, early HandshakeDone handling, the handshake-to-DATA parser boundary, TCP partial-frame buffering, and fail-closed behavior for fatal handshake/cryptographic errors. These are adopted draft requirements, not proof that all malformed-frame and ordering tests have passed. Duplicate-frame handling, unsupported-version outcomes, timeout behavior, and controlled HB-01/HB-02 receiver-level injection remain open for verification. The base protocol continues to omit peer identity authentication by design.

## Existing documented wire behavior

1. A connection in Handshake sends a PublicKey frame containing a 32-octet payload containing the local X25519 public key.
2. A receiver checks PublicKey length and accepted flags; the current Linux implementation permits COMPRESSION_CAPABLE.
3. Upon receiving the peer PublicKey, the endpoint derives directional traffic keys and sends an empty HandshakeDone.
4. HandshakeDone may arrive before PublicKey. Ready is reached only when traffic keys are derived and the peer HandshakeDone was received.
5. The current base handshake does **not** authenticate peer identity; an active man-in-the-middle remains possible. HandshakeDone does not authenticate the transcript.

## Candidate normative rules requiring implementation verification

The following is **candidate wording**, not a claim that all current implementations comply; the 32-octet PublicKey format was confirmed in the 2026-11-07 Linux/Zephyr interoperability checks:

- **HS-1 — PublicKey length:** A receiver **MUST** reject a PublicKey frame whose payload length is not exactly 32 octets.
- **HS-2 — HandshakeDone length:** A receiver **MUST** reject a HandshakeDone frame with a nonempty payload.
- **HS-3 — Readiness:** An endpoint **MUST NOT** deliver protected application DATA as established traffic until its traffic keys are available and it has processed the peer HandshakeDone.
- **HS-4 — Stream framing:** An endpoint **MUST** handle a PublicKey or HandshakeDone split across multiple TCP reads, and **MUST NOT** interpret incomplete frames as complete messages.
- **HS-5 — Security claim:** Implementations **MUST NOT** treat the unauthenticated base key exchange as proof of peer identity. This is an intentional protocol boundary, not a pending feature. Applications needing identity authentication must provide it separately above STCP or through another explicitly specified mechanism outside the base protocol.

## Decisions blocked pending code and negative tests

| Question | Why it matters | Evidence needed |
| --- | --- | --- |
| PublicKey length | Verify rejection of lengths other than 32 octets on Linux and Zephyr | Cross-platform malformed-frame negative vectors |
| Flags on PublicKey and HandshakeDone | Which bits are mandatory, optional or invalid? | Decoder checks and cross-platform malformed-frame tests |
| Duplicate PublicKey | Retransmission, key replacement, replay ambiguity | Both implementations' state transitions |
| Duplicate or early HandshakeDone | Must be deterministic without permitting early DATA | Permutation tests and negative cases |
| DATA before Ready | Explicit error/drop/buffer semantics | Wire-level trace and implementation tests |
| Handshake timeout | Prevent stalled peers consuming resources indefinitely | Carrier-specific timers and observable outcomes |
| Version mismatch / unknown frame type | Specify reject vs close vs reset | Negative vectors on TCP and UDP |
| Connection-ID binding | Prevent cross-connection frame confusion | Source trace and multi-connection tests |
| Reconnect / fresh keys / nonce rollover | GCM nonce uniqueness and key lifetime | End-to-end crypto and reconnect tests |
| Peer authentication | **RESOLVED: out of scope by design.** STCP does not authenticate peer identity and will not add a TLS-like identity/PKI layer. | State limitation and active MITM risk unambiguously in Security Considerations |

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
5. Document the intentional absence of peer identity authentication and its active MITM consequences in Security Considerations; review UDP congestion safety separately as a publication-critical open issue.

This document intentionally makes **no production code changes** and does not claim the protocol is ready for Standards Track publication.
