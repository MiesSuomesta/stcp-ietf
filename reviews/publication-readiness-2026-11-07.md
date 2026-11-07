# STCP Standards Track Internet-Draft — Publication Readiness Review

Date: 2026-11-07
Scope: draft-paxsudos-stcp-00.xml on work/experimental-draft-finalization-20261107, the source review, and the 2026-11-01 Linux–Zephyr LTE interoperability report.

## Status

The author reports that the GitHub Actions xml2rfc workflow passed. This establishes successful formatting/rendering under that workflow, **not** IETF acceptance, security certification, or protocol conformance.

**Recommendation:** suitable for continued development and potentially an early individual Internet-Draft submission after a focused editorial/technical consistency pass. Not yet ready to be represented as a complete interoperable Standards Track specification or an approved RFC.

## Publication priorities

### P0 — resolve before claiming a stable interoperable wire specification

1. **Independent known-answer vectors.** Publish deterministic examples for the 17-octet header, X25519/HKDF directional keys, IV, encrypted DATA and protected controls. The current text describes algorithms but the reviewed evidence does not establish independent vectors across platforms.
2. **Handshake and DATA boundary.** Confirm the behavior when PublicKey, HandshakeDone, and DATA arrive in one TCP read. The technical source review identifies an unresolved Linux/Zephyr parser-boundary question.
3. **UDP framing and failure behavior.** Define or explicitly scope out datagram-to-frame mapping, truncation, malformed trailing bytes, timeout handling and reliability/congestion behavior. The 2026-11-01 STCP-over-UDP download and full-duplex cases failed; their root cause is not established.
4. **Counter/nonce and session lifecycle.** Verify reconnect/reset behavior, nonce uniqueness, sequence wraparound and fatal-error paths across implementations. The source review identifies partial evidence but not complete coverage.

### P1 — editorial and Standards Track framing before first public submission

5. **Standards Track scope and maturity.** State the protocol requirements and deployment limits, and identify the interoperability and security evidence still needed to support a Proposed Standard.
6. **Implementation vs normative requirements.** Clearly distinguish observed Linux API constants, fixed windows, RTO values and frame-size limits from interoperable wire requirements.
7. **Security threat model.** Retain the explicit decision not to authenticate peer identity; X25519 plus AES-GCM does not prevent an active MITM during the handshake. Maintain fail-closed rules for fatal errors without confusing packet loss with fatal violations.
8. **IANA scope.** Keep the current statement that no permanent IP protocol number is requested. AF_STCP local API values 253/254 must not be confused with outer IP protocol numbers.
9. **Document consistency.** The technical source review header still calls the target Standards Track/Proposed Standard, despite the Experimental decision. Align it in a separate editorial update, retaining the historical technical findings.
10. **Submission metadata and checks.** Confirm intended status, author/contact metadata, required IETF boilerplate and submission checks against the rendered output before uploading. Successful xml2rfc rendering alone does not establish successful I-D submission.

## Evidence now available

- Linux–Zephyr nRF9151 over LTE, 2026-11-01: STCP-over-TCP upload, download and full duplex PASS at 3,000 bytes per direction; client and Linux server byte counts agree.
- STCP-over-UDP upload PASS; download FAIL with server timeout; full duplex failed on client with no final server result in reviewed log.
- The benchmark report is test-harness evidence, not an independent cryptographic audit or exhaustive conformance suite.

## Suggested next actions

1. Add a short Scope and Deployment Considerations section to the Internet-Draft without asserting unverified capabilities.
2. Reconcile stale status text in the source-review introduction.
3. Build deterministic wire/KDF test vectors from the actual implementation, then compare against Zephyr.
4. Keep the UDP failures and remaining security/lifecycle questions in the issue list rather than masking them.
5. Re-run xml2rfc and conduct a human review of the generated text before submission.

This review is an engineering readiness checklist, not a formal IETF review or approval.
