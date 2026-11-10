# Linux vs Zephyr socket send error contract — 2026-11-10 HEADs

Read-only source comparison of uploaded STCP and SDK bundles. No runtime tests and no production changes.

## Linux implementation

`STCP/kernel/module/src/stcp_ops.c`, `stcp_sendmsg` approximately lines 926–1017:

- Holds per-socket `tx_lock`, copies up to `STCP_IO_BUFFER_MAX` bytes into its TX buffer, then calls `stcp_rust_send`.
- On `-EAGAIN`, nonblocking sends stop; blocking sends wait on `recv_wq` and retry until ready, interrupted or timeout.
- Blocking wait timeout explicitly assigns `-ETIMEDOUT`.
- If a **previous outer chunk** has succeeded, a later negative return is replaced with the positive `total` already accepted. A short positive Rust result is also returned as a partial count.
- **Important limit:** this wrapper cannot account for partial frames internally committed by a **single** `stcp_rust_send` call that itself returns a negative error. Therefore it does not universally eliminate the ambiguous-commit risk identified in the Rust session source.

`STCP/kernel/module/rust/src/session.rs`, `send` approximately lines 938–1170:

- Splits the input into frames according to `frame_payload_len(ctx)`.
- On reliable UDP, each frame is enqueued and its nonce/sequence advanced before `send_frame`.
- A later `send_frame(...)?` failure returns an error even if earlier frames of the **same Rust call** were already accepted.
- The successful result is `Ok(data.len())`; no partial success is returned by this Rust function on an intermediate carrier error.

## Zephyr comparison

`SDK/Zephyr/common/module/src/stcp_socket_offload.c`, `stcp_send_common_locked`:

- Converts negative Rust errors to socket `-1`/`errno` (apart from blocking EAGAIN retry).
- A blocking send deadline returns EAGAIN, not ETIMEDOUT, in the inspected wrapper.
- As on Linux, a single negative Rust return can obscure internally committed frames.

## Assessment

Both platforms share a **source-level possibility** of ambiguous partial commit within a multi-frame Rust send. Linux additionally reports partial progress across successfully completed **outer C chunks**; Zephyr's wrapper behavior differs. The Linux-versus-Zephyr timeout errno difference is local API behavior, not a wire-format mismatch.

The source alone does not establish a reproducible duplicate-delivery bug. Avoid asserting an all-or-nothing socket send contract, or proposing changes before deterministic carrier-fault tests.

## Next tests

- Inject failure on the second UDP frame **within one Rust send** on both platforms; record caller return, pending queue, wire frames and receiver bytes.
- Inject failure in a later Linux C outer chunk; verify positive partial return.
- Verify blocking timeout errno on each platform.
- Retry the same application buffer after a reported error and check whether application-visible bytes repeat.
- Preserve build revisions, effective frame payload, socket flags and carrier error type in test evidence.

No source code changed; no tests run.
