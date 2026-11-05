# Handshake-to-DATA boundary: targeted interoperability regression plan (2026-11-04)

**Status:** test specification only. No live execution or production source modification is claimed.

## Source basis

- `internet-draft/STCP-STATE-MACHINE-SOURCE-REVIEW-2026-11-02.md`
- `internet-draft/STCP-LINUX-ZEPHYR-STATE-COMPARISON-2026-11-02.md`
- `internet-draft/draft-paxsudos-stcp-00.xml`

The 2026-11-02 comparison found that the Linux handshake parser checks for completion before extracting the next queued frame. The inspected Zephyr parser instead continued extracting frames in its handshake loop and rejected non-handshake types. This is a **suspected boundary divergence**, not a reproduced bug. The 2026-11-04 785/785 hardware echo run does not prove that the boundary permutations below were exercised.

## Test preconditions

- Use matching, recorded Linux and Zephyr source revisions and configuration.
- Use a valid, fully specified PublicKey (64 octets), valid empty HandshakeDone, and a cryptographically valid DATA frame generated with the negotiated session keys. Do **not** use an arbitrary unencrypted DATA frame and interpret rejection as a parser failure.
- Preserve the STCP wire header, full ciphertext and tag, and a deterministic application payload; independently verify the expected plaintext.
- Control carrier write batching and read segmentation. TCP writes alone do not guarantee that the receiver sees the same batches; instrument or gate the receiver so queued bytes and parser invocation order are verified.
- Keep client/server role and packet direction explicit, with distinct session keys and nonce counters.

## Cases

| ID | Input sequence | Delivery condition | Expected observable result |
| --- | --- | --- | --- |
| HB-01 | PublicKey, HandshakeDone, DATA | All bytes queued before handshake parser resumes | Endpoint enters Ready; DATA delivered exactly once; no Protocol error |
| HB-02 | HandshakeDone, PublicKey, DATA | All bytes queued before parser resumes | Endpoint enters Ready; DATA delivered exactly once; no Protocol error |
| HB-03 | PublicKey, HandshakeDone, DATA | Header and payload split across multiple TCP reads | Endpoint enters Ready; DATA delivered exactly once; no Protocol error |
| HB-04 | PublicKey, HandshakeDone | HandshakeDone header/payload split across reads | Endpoint reaches Ready only after complete HandshakeDone |
| HB-05 | PublicKey, malformed HandshakeDone (nonempty payload) | Same queued batch | Reject malformed handshake; do not deliver application DATA |
| HB-06 | PublicKey with invalid payload length | Fragmented and unfragmented variants | Reject malformed handshake; do not enter Ready |
| HB-07 | PublicKey, HandshakeDone, DATA, DATA | Same queued batch, distinct valid sequence/nonce values | Both DATA payloads delivered in order exactly once |
| HB-08 | HandshakeDone, PublicKey, DATA | Repeat on both peer roles | Equivalent externally visible behavior for both client and server |

## Platform matrix

1. Linux STCP receiver over TCP, with controlled peer fixture.
2. Zephyr STCP receiver over TCP, with controlled peer fixture.
3. Linux ↔ Zephyr live TCP echo/traffic capture as corroboration.
4. UDP cases **deferred** until datagram framing and congestion behavior are specified; do not silently reuse TCP assumptions.

## Pass/fail criteria

**PASS** requires a valid cryptographic frame, verified input ordering/queueing, exactly-once plaintext delivery where expected, and no terminal protocol error for valid sequences. A mere successful connect or echo after unconstrained scheduling is insufficient.

**FAIL** requires a reproducible observed divergence, with source revision, raw input bytes or packet capture, parser trace, endpoint state and error. Mark unexecuted tests **NOT RUN**, not PASS or FAIL.

## Required evidence fields

- UTC timestamp; host/device identifiers and firmware hashes; Linux and Zephyr commit SHAs
- Carrier; endpoint role; input-frame order; TCP segmentation and confirmed receiver queue state
- Wire capture/fixture hash; expected and observed plaintext length and SHA-256
- Expected and observed transition to Ready; parser result; terminal errno
- Repetition count and outcome; whether the failure is deterministic

## Draft consequence

If HB-01/HB-02 show the suspected Zephyr parser issue, correct the implementation and rerun before making broad cross-platform claims. The wire-level requirement to preserve and process valid post-handshake DATA must be specified independently of any Linux-specific parser implementation. No peer-identity authentication is proposed; its absence is already documented in the draft.

## Source recheck — 2026-11-05 08:37:52 bundles

Inspected the user-provided archives `stcp-project-05.11.2026-083752-STCP.zip` (`kernel/module/rust/src/session.rs`) and `stcp-project-05.11.2026-083752-SDK.zip` (`Zephyr/common/module/rust/src/session.rs`). Both handshake parsers check `have_handshake_inputs` **before** extracting the next wire frame. Their check combines a received/persisted peer HandshakeDone with a received peer key or ready crypto state. This supersedes the historical 2026-11-02 Zephyr missing-guard hypothesis for these sources.

Executed the archived `tests/test_handshake_boundary.py` against those two extracted real source files: **5/5 PASS** (four model tests and one source-contract check). This is not an execution of the production parsers and does not validate cryptographic DATA decoding or actual receiver queue coalescing.

The developer separately reported **100/100 PASS** Linux AF_STCP → Raspberry Pi STCP echo exchanges (257-byte payload each) using the blocking-connect regression script. This is live application-level evidence, not controlled HB-01/HB-02 evidence.

**HB-01/HB-02 status remains NOT RUN.** The next implementation step is a test-only deterministic receive-queue/parser harness, with valid negotiated DATA ciphertext and a verified exactly-once plaintext result. Do not count source-contract PASS as hardware HB PASS.
