# Linux UDP reliability runner review — uploaded 2026-11-10 HEAD

Source-only inspection of `tests/kernel/testing/reliability-test.sh` and `stcp_udp_reliability_test.c` from uploaded STCP bundle. No test executed; no production source changed.

## Confirmed harness defects

- Shell script line 33 invokes the test binary with **no argument**, but its `main` (C lines 101–107) requires `server` or `client`; it returns 2 otherwise. Thus the current runner cannot pass as written.
- The script starts the server **before** its first module reload (shell line 40 vs lines 11–19), so server setup and module lifecycle are inconsistent.
- Every case removes/reinserts the STCP module (lines 12, 17, 35), potentially disrupting unrelated active STCP sockets; the script has no isolation check.
- Both `rmmod` and `insmod` failures are suppressed with `|| true`, allowing tests to run against an unexpected module state.
- No bounded timeout or cleanup trap protects the background server. The runner's final PASS banner would not be reliable evidence if setup and teardown were not verified.

## Safe gate

Do **not** run this script on a shared development machine. First collect non-destructive `uname -r`, `lsmod`, module path, and existing process/port information. On an isolated host, compile the C test and run explicit server/client roles with watchdog and cleanup, then separately evaluate fault modes with verified module state and restored parameters. Never unload a production or in-use STCP module just to run this test.

## Additional observation

The C client sends a deterministic 256-KiB payload and verifies a 2-byte reply; the server validates every received byte. This makes the C program a useful test primitive once correctly orchestrated, but not a proven runnable suite by itself.

No test results claimed.
