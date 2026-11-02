# STCP Internet-Draft publication readiness review

Review date: 2026-11-02
Scope: internet-draft/draft-paxsudos-stcp-00.xml in the stcp-ietf repository.
This is an editorial/technical gap review, not an IETF review or approval.

## Confirmed from developer test output

- xml2rfc 3.35.0 successfully rendered the draft to a 20 KB text file.
- The initial render produced two metadata warnings. The subsequent Git commit da7f9be added an explicit consensus attribute and an abbreviated title. A clean rerun after that commit has **not yet been reported**.
- Independent Python cryptographic vector tests: developer-reported 5/5 PASS.
- Live Linux AF_STCP TCP loopback C test: developer-reported PASS with 1024 bytes client-to-server and 257 bytes server-to-client.
- No kernel changes were made for these IETF tests.

## Publication and technical gaps

| Priority | Area | Observed in current draft | Required follow-up |
| --- | --- | --- | --- |
| P0 | Security: peer authentication | Handshake exchanges unauthenticated X25519 public keys and HandshakeDone is unauthenticated. Active MITM remains possible. | Decide whether the draft explicitly specifies unauthenticated encryption only, or defines a peer-authentication mechanism. Avoid claiming authenticated secure transport until resolved. |
| P0 | UDP congestion control | Fixed eight-frame window and retry limits are documented, but not a complete congestion-control algorithm. | Specify and test safe congestion behavior before claiming general Internet UDP deployment readiness. |
| P0 | Normative interoperability | Many paragraphs describe the observed Linux implementation, not mandatory behavior for independent implementations. | Define interoperable wire-level requirements, failure cases, limits and state transitions with consistent MUST/SHOULD/MAY language. |
| P1 | Cryptographic lifecycle | Nonce uniqueness across reconnects and key lifecycle remains unverified. | Specify nonce allocation, key freshness, sequence rollover and reconnect behavior; validate against actual implementations. |
| P1 | Handshake and state machine | Partial handshake flow documented; error handling and timeouts incomplete. | Define message ordering, duplicate handling, invalid inputs, timeouts and state transitions. |
| P1 | UDP framing and errors | One/multiple frames per datagram, truncation and trailing bytes are explicitly open. | Choose and test normative datagram framing and malformed-packet behavior. |
| P1 | Compression | COMPRESSION_CAPABLE is mentioned but negotiation and security behavior are incomplete. | Specify negotiation, format, limits, and interaction with encryption. |
| P1 | Cross-platform interoperability | Linux TCP loopback and independent Python vectors do not prove Linux/Zephyr wire agreement. | Test Linux ↔ Zephyr over relevant carriers, compare wire captures, crypto vectors, errors and reconnects. |
| P1 | IANA | Draft requests no IANA allocation and distinguishes Linux AF_STCP API selectors from IP protocol numbers. | Keep no-allocation position unless a new protocol registry or codepoint allocation is actually required. |
| P2 | RFC references and boilerplate | Draft currently has no references section; it names algorithms and normative requirements. | Add appropriate normative references, RFC 2119/8174 terminology, and relevant transport/security references after normative decisions. |
| P2 | Document metadata | First render warned about consensus default and running title; edits were committed. | Rerun xml2rfc and inspect output and warnings; do not mark clean until verified. |
| P2 | CI evidence | GitHub Actions workflow exists, but its result has not been verified in this review. | Inspect workflow runs, fix any RFCXML or vector failures, and retain run URLs/logs. |

## Suggested publication sequence

1. Re-render the updated RFCXML and record all warnings/errors.
2. Add standards terminology and accurate normative references without overstating current security.
3. Separate verified Linux-specific implementation behavior from protocol requirements.
4. Decide whether the first draft is an early, explicitly incomplete discussion draft or a proposed interoperable specification.
5. Define and test handshake error behavior, key/nonce lifecycle, UDP framing and congestion handling.
6. Run independent Linux/Zephyr interoperability tests and record reproducible artifacts.
7. Review IETF submission requirements and submit only with an accurate maturity/status description.

## Boundaries

A syntactically valid Internet-Draft can be submitted for discussion without being a finished standard. This checklist does not claim the current draft is secure against active attackers, deployable over arbitrary UDP networks, interoperable across platforms, approved by IETF, or ready for Standards Track adoption.

No STCP kernel or SDK source modifications are requested by this review.
