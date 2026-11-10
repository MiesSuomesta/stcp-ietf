# Zephyr ETH/LTE Rust build-selection check — 2026-11-10 HEAD SDK

Read-only source/config inspection of user-uploaded `stcp-project-10.11.2026-181823-SDK.zip`. No build or hardware test.

## Findings

- `Zephyr/common/apps/application/ethernet.conf` sets `CONFIG_STCP=y` (line 128) and `CONFIG_STCP_MAX_SOCKETS=2` (line 130).
- `Zephyr/common/apps/application/lte.conf` sets `CONFIG_STCP=y` (line 1).
- `Zephyr/common/module/Kconfig` declares `menuconfig STCP_RUST_CORE` with `default y` (lines 80–87), which selects the Rust core by default if its dependencies and merged configuration allow it.
- Neither application overlay explicitly sets `CONFIG_STCP_RUST_CORE=y`. Thus the overlays alone do **not** establish the final resolved setting.
- The uploaded SDK archive contains application configuration overlays but no final generated `build/zephyr/.config` for either target. The actual firmware configuration is **not independently verified** here.
- `Zephyr/common/module/src/stcp_rust_platform.c` lines 678–705 sends each UDP STCP frame with one `zsock_send` call and treats short send as `-EIO`; a send interrupted by `EINTR` is retried. This behavior is contingent on the Rust path being compiled and selected.

## Required evidence before asserting the tested path

Capture the resolved `CONFIG_STCP_RUST_CORE`, `CONFIG_STCP`, carrier selection, heap size, socket count, and buffer pool values from **each** final ETH/LTE `build/zephyr/.config`, along with build hash and exact source commit. If such evidence exists in the separate log archive, cite it by filename and line rather than treating source defaults as build proof.

No production code changed; no tests executed.
