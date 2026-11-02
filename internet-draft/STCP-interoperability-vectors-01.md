# STCP interoperability test vectors — revision 01

Status: independently computed candidate vectors, **not yet confirmed by Linux/Zephyr runtime tests**. Source basis: 2026-11-02 Linux module `kernel/module/rust/src/frame.rs` and `kernel/module/src/stcp_crypto.c`. All hex strings are lowercase, concatenated octets. These are PUBLIC test keys and MUST NOT be used in production.

## X25519

Client private: `77076d0a7318a57d3c16c17251b26645df4c2f87ebc0992ab177fba51db92c2a`

Server private: `5dab087e624a8a4b79e17f8b83800ee66f3bb1292618b6fd1c2f8b27ff88e0eb`

Client public: `8520f0098930a754748b7ddcb43ef75a0dbf3a0d26381af4eba4a98eaa9b4e6a`

Server public: `de9edb7d7b7dc1b4d35b61c2ece435373f8343c85b78674dadfc7e146f882b4f`

Shared secret: `4a5d9d5ba4ce2de1728e3bf480350f25e07e21c947d19e3376f09b3c1e161742`

## STCP directional KDF

Salt: SHA256(ASCII("STCPv4-AES256-GCM-HKDF-SHA256") || client_public || server_public).

Salt: `68789ffabafa9cb7c2895c3a211ef17aadbdc15a22669984f0cfdfbeddcc6fdd`

PRK: HMAC-SHA256(salt, shared secret).

PRK: `6bd56a3c28264f96f858a078e0a34e5002cc39f6e8cbe0f8ed6b724fbacbb9aa`

Client-to-server key: HMAC-SHA256(PRK, ASCII("STCPv4 AES256-GCM client to server key") || 0x01).

C2S: `4a78b69f86818b6027f82f9b21cfa799083898eaa988d9ef70ce8ddff650c62e`

Server-to-client key: HMAC-SHA256(PRK, ASCII("STCPv4 AES256-GCM server to client key") || 0x01).

S2C: `a58ede41164232df21c8d31852d0c7863afb9ca54defd3126615d63f5d280e51`

C2S control key: HMAC-SHA256(C2S, ASCII("STCP wire3 control AES256-GCM key") || 0x01).

C2S control: `a7870e1b81b0f5f850f06a429ebbadbae20c9bbcd7806141c0c2bdd25d16ae88`

ASCII labels exclude the trailing NUL.

## DATA frame example

Wire version 3; DataChunk packet type 3; flags 0; payload length 29 (8 nonce + 5 ciphertext + 16 tag); sequence 1; acknowledgment 0; connection ID 0x12345678.

Header (17 octets): `330000001d000000010000000012345678`

Plaintext UTF-8: `hello` (hex `68656c6c6f`).

Nonce (8 octets): `0000000000000001`

AES-256-GCM IV (12 octets): `000000000000000000000001`

AAD: the exact 17-octet header above.

Ciphertext + 16-octet tag: `8f577af326079aae12b967b491f1edf9a00ff91477`

Full frame: `330000001d00000001000000001234567800000000000000018f577af326079aae12b967b491f1edf9a00ff91477`

## Authenticated ACK frame example

Wire version 3; Ack packet type 5; flags 0; payload length 24; sequence 0; acknowledgment 1; connection ID 0x12345678.

Header (17 octets): `3500000018000000000000000112345678`

Nonce: `0000000000000001` (under the **distinct C2S control key**, not the C2S DATA key).

Plaintext: empty; AAD: ACK header; AES-GCM authentication tag: `2ee2a428086309e892dd4d9cb4c97715`

Full frame: `350000001800000000000000011234567800000000000000012ee2a428086309e892dd4d9cb4c97715`

## Validation status and limitations

- Computed using Python cryptography (X25519 and AESGCM) and Python hashlib/hmac, independently of the STCP runtime.
- Frame layout, key labels, HMAC ordering, 4-zero-octet GCM IV prefix, and control-key separation are based on the reviewed Linux source.
- Runtime comparison against the Linux kernel module, Zephyr implementation, and SDK remains **TODO**.
- The example is a primitive/frame known-answer vector, not a full handshake transcript or a guarantee that this exact connection ID, sequence, nonce and ACK combination is reachable as a valid live session.
- Never reuse test keys or deliberately fixed nonces in production.
