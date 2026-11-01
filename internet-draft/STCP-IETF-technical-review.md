# STCP 9.0.3-ietf — Consolidated Internet-Draft technical review

**Status:** Source review in progress; not an audit certification.  
**Proposed author:** Lauri Jakku, Paxsudos IT.  
**Target:** Individual Internet-Draft `draft-paxsudos-stcp-00`, intended status Experimental.

## 1. Wire format and framing (review 01)

## Verified from kernel/module/rust/src/frame.rs

- Active Rust module imports `frame` from `lib.rs`.
- Compact header is 17 octets: descriptor (1), payload length (4), sequence (4), acknowledgment (4), connection ID (4).
- Integers use network byte order (big-endian).
- Descriptor bits 0–3 encode packet type, 4–5 wire version, 6–7 flags.
- Wire version constant is 3, distinct from product version 9.0.3-ietf.
- Types: PublicKey=1, HandshakeDone=2, DataChunk=3, DataChunkEnd=4, Ack=5, Ping=6, Pong=7, Close=8, Reset=9.
- Header decode rejects unknown versions/types and excessive payload lengths.
- PublicKey max payload 64 bytes; HandshakeDone max payload zero.
- Constants: nonce 8 bytes; authentication tag 16 bytes; UDP frame payload 60 KiB; stream frame payload 2 MiB. Distinguish these limits from maximum application message size.
- FLAG_COMPRESSED=1 and FLAG_COMPRESSION_CAPABLE=2 are logical values encoded in descriptor flag bits.

## Verified from kernel/module/rust/src/crypto.rs

- X25519 key exchange via C FFI, with 32-byte secret and 32-byte public key stored in a 64-byte wire key structure.
- Separate client-to-server and server-to-client session keys, plus derived control keys.
- AES-256-GCM is used for encrypted payloads and control tags.
- Encryption/decryption accepts associated authenticated data (AAD), which may authenticate the header depending on call sites; trace these before making a normative claim.
- Authentication tag length 16 bytes; nonce passed as u64 to C backend.
- Self-test includes altered ciphertext, wrong AAD, wrong nonce and direction checks. This is a code-level self-test, not proof of full protocol security.

## Unresolved before writing normative RFC language

1. Trace all session and carrier call sites to identify exactly which header bytes are used as AAD for each packet type.
2. Inspect C implementation of nonce encoding, key derivation, entropy source and GCM requirements.
3. Specify handshake ordering, replay prevention, authentication guarantees, and key lifetime.
4. Confirm reliability and congestion-control behavior from current active sources, not historical backups.
5. Locate actual Zephyr STCP protocol implementation (the `ethernet` ZIP contains network drivers, not necessarily the application-level STCP stack).
6. Define error processing, unknown flags, protocol-version negotiation and limits.
7. Establish IP protocol 253 experimental usage and IANA considerations without claiming a permanent allocation.
8. Generate independent wire-format test vectors and verify multiple implementations.

## Security note

This report intentionally excludes credentials and other secrets. Do not submit the source bundles to IETF; submit the protocol specification only.

## 2. Handshake and state machine (review 02)

## Reviewed source paths
- kernel/module/rust/src/session.rs
- kernel/module/rust/src/crypto.rs
- kernel/module/rust/src/state.rs

## Confirmed implementation behavior
1. SocketState enumerates New, Bound, Listening, Handshake, Ready, Closed, Error (state.rs:44–52).
2. start_handshake() requires Handshake state and an attached carrier, sends PublicKey, then calls progress_handshake() (session.rs:496–528).
3. PublicKey is 64 bytes, the first 32 bytes containing the X25519 public key; send_public_key sets FLAG_COMPRESSION_CAPABLE (session.rs:540–580; crypto.rs:47–50).
4. The receiver rejects PublicKey frames of lengths other than 64 and flags other than FLAG_COMPRESSION_CAPABLE; HandshakeDone must have zero payload (session.rs:613–625).
5. The parser explicitly supports HandshakeDone arriving before PublicKey. It stops at the handshake boundary so as not to consume application DATA (session.rs:596–637).
6. Receiving the peer key triggers derive_session_keys() and sending a HandshakeDone (session.rs:638–657).
7. Ready requires both crypto.ready() and peer_handshake_done (session.rs:659–693).
8. Crypto derives distinct client-to-server and server-to-client keys from X25519 shared secret and ordered client/server public keys, via C FFI; directional control keys are subsequently derived (crypto.rs:51–102).
9. The UDP carrier creates server children on receipt of the first PublicKey rather than from an in-kernel registry before receiving the datagram (session.rs:318–327).

## Important open security / interoperability questions
- The shown handshake exchanges public keys but does not itself demonstrate peer identity authentication. Assess active MITM exposure and whether external authentication or pinned keys are supported.
- HandshakeDone has no payload and is not shown here as cryptographically authenticated. Verify protection and transcript binding before making security claims.
- Inspect C implementation of stcp_kernel_derive_session_keys, including KDF algorithm, salt, labels and context binding.
- Verify replay resistance, connection-ID binding, nonce uniqueness and all control-packet authentication paths.
- Verify client/server role and simultaneous connection behavior across carriers and Zephyr.
- Establish whether reserved 32 bytes of PublicKey are validated or ignored; define normative handling.
- Confirm experimental IP protocol number usage and transport carrier mapping from the current code, rather than historical assumptions.

## RFC drafting status
This report documents observed code paths, not yet a normative RFC specification or an independent security audit. Do not claim authenticated key exchange until identity authentication is established.

## 3. Kernel C cryptographic derivation — new source findings

Sources: `kernel/module/src/stcp_crypto.c` lines 109–165; `kernel/module/rust/src/crypto.rs` lines 35–104; `kernel/module/rust/src/kdf.rs`.

- Rust `CryptoContext::derive_session_keys` calls `stcp_kernel_x25519_shared`, then `stcp_kernel_derive_session_keys` via FFI.
- C key derivation hashes the concatenation of ASCII domain `STCPv4-AES256-GCM-HKDF-SHA256`, the 32-byte client public key, and the 32-byte server public key to produce a 32-byte salt.
- It uses HMAC-SHA256 with that salt and the 32-byte X25519 shared secret to produce a PRK.
- It computes directional 32-byte keys with HMAC-SHA256(PRK, ASCII direction label || byte 0x01). Labels are `STCPv4 AES256-GCM client to server key` and `STCPv4 AES256-GCM server to client key`.
- Rust assigns directional TX/RX keys according to client/server role, and derives separate control keys using HMAC-SHA256(data_key, `STCP wire3 control AES256-GCM key` || 0x01).
- `kdf.rs` also contains a separate `derive_directional_keys` with `STCPv2` domain and labels. This is **not** the function invoked by the reviewed `CryptoContext::derive_session_keys` path; document only the active derivation after checking other call sites.
- X25519 shared-secret generation rejects a failed kernel `curve25519` call. Derived equal directional keys are rejected. C clears salt and PRK before return.
- **Open security issue:** The reviewed exchange sends public keys without showing an authenticated identity binding. AES-GCM protects data once keys are established, but this alone does not prevent an active man-in-the-middle during unauthenticated key exchange. Do not claim peer identity authentication without further evidence.
- **Open interoperability issue:** Protocol/product/wire/KDF label versions (`9.0.3-ietf`, wire3, `STCPv4`, and legacy `STCPv2`) differ. Explain their distinct meanings and establish exact test vectors before RFC publication.

## 4. Next verification tasks

1. Trace all callers of `derive_directional_keys` and C FFI to identify live vs legacy paths across platforms.
2. Trace `authenticated_control_frame`, `authenticate_control`, and `authenticate_data_frame` to enumerate exact AAD and nonce bytes.
3. Verify peer identity authentication or document explicit absence and threat model.
4. Compare Zephyr and SDK wire and KDF implementations with Linux; generate deterministic interop test vectors.
5. Specify replay, sequence wraparound, key rotation, congestion and flow control behavior.

## 5. DATA and control authentication, nonce and replay (review 06; 2026-11-01)

Source: `stcp-project-01.11.2026-112352-STCP.zip`, `kernel/module/rust/src/session.rs`, `crypto.rs`, `control.rs`.

- DATA transmission constructs a 17-byte encoded header, writes an 8-byte big-endian nonce and calls `crypto.encrypt_into(nonce, &header, wire_plaintext, ...)` (session.rs:987–1027). The full encoded header is AES-GCM AAD.
- DATA reception uses `crypto.decrypt_in_place(nonce, &frame.header.encode(), ...)` before admitting data to the reordering path (session.rs:1280–1297). This verifies the header as AAD and the ciphertext tag.
- DATA transmission advances `tx_nonce` and `tx_sequence` after encryption and successful pending-frame allocation (session.rs:1030–1047); retransmission storage retains encrypted frame bytes. Check all retransmission paths and failure semantics before asserting end-to-end nonce uniqueness.
- In-order DATA requires `frame.header.sequence == expected_rx_sequence` AND `frame.nonce == expected_rx_nonce` (session.rs:1370–1384, 1425–1440). This is an in-order replay rejection mechanism; out-of-order buffering is authenticated first.
- Control packets (ACK, Ping, Pong, Close, Reset) use a separate derived control key and 8-byte nonce plus 16-byte AES-GCM tag over empty plaintext, with the encoded header as AAD (control.rs:1–40, crypto.rs:104–119).
- Control transmission reserves `tx_control_nonce` under a lock before encoding (session.rs:1500–1511). Control reception verifies the tag before accepting the nonce into a 64-position sliding replay window (session.rs:1514–1523, control.rs:43–71).
- Control replay window accepts unseen values within 63 below the highest, rejects duplicates and values 64 or more behind. A unit test covers reordering, duplicates, boundaries (control.rs:73–85).

### Security boundaries and remaining checks

- These are code observations, **not** independent proof of nonce uniqueness under all concurrency, retries, crashes, rekeying or transport paths. Audit C AES-GCM nonce-to-IV encoding, retransmission behavior and lifecycle reset.
- AAD authenticates headers **after a session key is established**; it does not authenticate the identity of the peer during the ephemeral X25519 handshake.
- **Explicit design decision:** STCP base protocol does not require persistent identity keys, PKI or peer identity authentication. State clearly in Security Considerations that an active MITM can substitute keys during an unauthenticated handshake; do not imply AES-GCM prevents this.
- Handshake PublicKey and HandshakeDone frames are not shown to use these DATA/control authentication paths; separately document handshake tampering and downgrade considerations.
- Verify C cryptographic backend and SDK/Zephyr equivalence before making normative cross-platform claims.

## 6. AES-GCM IV construction and retransmission (review 07; 2026-11-01)

Sources: `kernel/module/src/stcp_crypto.c` lines 282–301; `kernel/module/rust/src/session.rs` lines 1015–1047 and 1682–1747; `kernel/module/rust/src/control.rs` lines 1–85.

- The C AES-GCM backend expands the 8-octet transmitted nonce into a 12-octet GCM IV by prepending four zero octets and writing the 64-bit nonce in big-endian order. This is a **fixed prefix**, not a per-packet random salt.
- The 17-octet DATA header is AAD; the 8-octet nonce precedes ciphertext and the 16-octet authentication tag.
- Reliable DATA stores the complete encrypted frame as `PendingFrame.bytes`; retransmission clones and resends those stored bytes rather than re-encrypting the same nonce with a potentially different plaintext.
- Control frames authenticate the encoded header as AAD using a distinct derived control key; they contain the 8-octet nonce and 16-octet tag, with empty plaintext.
- A 64-entry sliding replay window rejects duplicate authenticated control nonces. DATA checks expected sequence and nonce before publishing plaintext, with authenticated out-of-order buffering.
- **Security limitation by design:** the base protocol does not authenticate peer identity; active handshake MITM remains possible. This is not an open request to add certificates or static keys.

### Remaining work

1. Verify nonce reset and session-key lifecycle across reconnect, errors and key reuse.
2. Verify that all alternate carriers and SDK/Zephyr implementations use identical IV construction and authenticated header encoding.
3. Review handshake tampering and state transitions, including unauthenticated HandshakeDone.
4. Construct deterministic known-answer vectors for header, IV, KDF, DATA and control frames.
5. Review sequence-number wraparound, replay window boundaries and nonce exhaustion.

**Assessment:** These are static source observations, not proof of complete protocol security or interoperability.

## 7. Connection lifecycle, counter exhaustion and fail-closed (review 08; 2026-11-01)

Source: `kernel/module/rust/src/session.rs` and `kernel/module/rust/src/frame.rs` from the reviewed 11:23:52 STCP source bundle.

- `frame.rs` uses 32-bit network sequence, acknowledgment and connection-ID fields; `Header::with_numbers` rejects values greater than `u32::MAX` (`frame.rs:90–110`). The internal counters are `u64`; this prevents silent wire truncation at the header-construction boundary.
- The DATA transmit path advances `tx_nonce` and `tx_sequence` with `checked_add` after allocating/encrypting a frame (`session.rs:1030–1070`), returning `Crypto` or `Protocol` errors on arithmetic overflow. **Not established:** whether every such error marks the socket terminal; `checked_add` by itself only returns an error.
- The DATA receive commit path checks exact expected sequence and nonce and uses checked increments (`session.rs:1370–1385`, `1425–1465`). A mismatch at the second commit check calls `protocol_error`, while the earlier mismatch returns `StcpError::Protocol` directly. Callers must be traced to determine whether both are terminal.
- `protocol_error()` invokes `fail_rx_error()`, which sets `SocketState::Error`, records a terminal errno, clears receive queues, sets `peer_eof` and wakes blocked readers (`session.rs:1829–1860`). This is evidence of a terminal receive-error path, not yet proof that all fatal errors follow it.
- Connection setup resets TX/RX DATA nonces and sequence counters (`session.rs:350–360`, `405–415`, `470–480`). **Open:** check all corresponding resets of control nonces, replay windows, cryptographic context and connection identifiers, including reconnect and reuse.
- Control transmission reserves its nonce with `checked_add` (`session.rs:1503–1511`); audit its overflow behavior and socket-state transition.
- The connection ID is allocated from an atomic counter in at least one connection setup path (`session.rs:335–348`). It is not established as a cryptographic session identifier; evaluate collision/wraparound and stale-packet handling.

### Required follow-up before normative RFC wording

1. Trace the callers of send/receive error returns to verify which errors actually transition to `Error`/`Closed` and which are retryable.
2. Inspect key regeneration and context reset for every reconnect and socket reuse path; test replay of frames from an earlier session.
3. Verify the 32-bit wire counter boundary with tests near `u32::MAX`; ensure failure occurs before unsafe reuse and define a protocol-level termination rule.
4. Distinguish malformed unauthenticated packets (potential denial-of-service input) from fatal authenticated state inconsistencies.
5. Compare SDK and Zephyr lifecycle semantics before making an interoperability claim.

**Design decision:** The base protocol has no mandatory peer-identity authentication or persistent identity keys. Fatal *established-session* integrity/state failures are intended to terminate the connection; ordinary packet loss and permitted reordering do not.

## 9. Key lifecycle and terminal receive errors (review 09, 2026-11-01)

Source inspected: `kernel/module/rust/src/state.rs`, `session.rs`, `crypto.rs` in the 2026-11-01 11:23:52 STCP bundle.

- `StcpContext::new()` and `StcpContext::connected_child()` each invoke `CryptoContext::new()` (`state.rs`, around lines 304 and 367). This establishes fresh crypto *objects*, but randomness quality and all reuse paths require separate review.
- `CryptoContext` implements `Drop`, clearing its secret key, TX/RX keys, and TX/RX control keys (`crypto.rs`, line 150). This does not alone prove that every transient copy or compiler-optimized memory region is securely wiped.
- During handshake, `session.rs` clones a crypto context, derives keys outside the lock, and publishes it by assignment (`session.rs`, around lines 640–654). Review concurrent handshake publication and cloned sensitive material lifetimes.
- `fail_rx_error()` sets `SocketState::Error`, records the terminal errno, clears several RX buffers and wakes receivers (`session.rs`, around lines 1831–1852). It does not explicitly clear or drop `inner.crypto` at that point. Determine whether connection teardown promptly releases the context and whether later operations are blocked.
- Connection setup resets TX/RX nonce and sequence counters (`session.rs`, around lines 353–356, 408–411, 475–478). Counter reset is safe only with appropriately fresh session keys; audit all reinitialization paths.
- DATA decryption uses the encoded frame header as AAD (`session.rs`, around lines 1287–1297), and in-order reception checks expected nonce and sequence (`session.rs`, around lines 1382 and 1428–1463). Further analysis needed for cross-session replay and UDP demultiplexing.

**Status:** Partial source-level evidence only; no dynamic test or cross-platform interoperability verification completed in this review.

**Next checks:** crypto constructor entropy, close/error lifecycle, UDP demux and connection-ID reuse, Zephyr application protocol implementation (not generic Ethernet driver), and SDK framing interoperability.

## 10. Connection identifiers, stale packets and terminal state (review 10, 2026-11-01)

Source: `kernel/module/rust/src/session.rs`, `frame.rs`, `state.rs` from 11:23:52 bundle. This is a static review; no replay injection tests performed.

- `NEXT_CONNECTION_ID` is an `AtomicU32` initialized to 1 (`session.rs:60`). Two connection setup paths allocate by `fetch_add(1, Ordering::Relaxed)` and skip zero (`session.rs:335–345, 392–400`). It is **not random** and wraps after the 32-bit range; the complete lifetime of IDs across every carrier/accept path remains to be checked.
- The wire header encodes a 32-bit connection ID in bytes 13–16 (`frame.rs:128`); decoding reconstructs it as a 32-bit value. This is a routing/demultiplexing field, not proof of peer identity.
- `authenticate_data_frame()` first checks `frame.header.connection_id == inner.connection_id`, then authenticates AES-GCM using the encoded header as AAD (`session.rs:1282–1298`). A stale DATA frame from an earlier session with distinct fresh keys should fail authentication even if IDs collide. This depends on session-key freshness and correct demultiplexing.
- The DATA send path checks `SocketState::Ready` before preparing a frame (`session.rs:902–914`). `tick()` returns `Ok(false)` for `Closed` and `Error` (`session.rs:1652–1661`). These observations do not prove every pending asynchronous send or control path is terminally blocked.
- `fail_rx_error()` marks `Error`, clears RX queues, and wakes readers (`session.rs:1831–1853`), but does not immediately wipe `inner.crypto`. Verify cleanup and lifetime, including concurrent references.

### Open issues before normative RFC language

1. Trace UDP listener demultiplexing and accepted-child connection-ID assignment, including address/port binding.
2. Confirm fresh X25519 keys for every new session, and exercise cross-session replay with forced connection-ID reuse.
3. Test ID wraparound, collisions and reconnects; distinguish harmless packet rejection from fatal authenticated state errors.
4. Audit send/control paths and pending retransmission queues after transition to `Error`.
5. Check Zephyr and SDK semantics against the Linux implementation.

**Provisional conclusion:** An old DATA packet is subject to both connection-ID matching and session-key authentication, but cross-session replay resistance is not yet proven end-to-end.
