# STCP Linux–Zephyr Ethernet BEN2 full-duplex test results — 2026-11-07

## Evidence and scope

The implementer supplied Linux BEN2 server logs for two runs using the physical Zephyr nRF9151 application with **Ethernet** carrier, not LTE. Transport was `stcp-tcp`, BEN2 request version 2, mode 3 (full duplex), 4096-byte chunks. Endpoint was a BEN2 server listening on port 19000. Results are based on user-provided logs, not independently rerun.

| Metric | 1 MiB per direction | 5 MiB per direction |
|---|---:|---:|
| Server status | PASS | PASS |
| Server RX bytes | 1,048,576 | 5,242,880 |
| Server TX bytes | 1,048,576 | 5,242,880 |
| Client TX bytes | 1,048,576 | 5,242,880 |
| Client RX bytes | 1,048,576 | 5,242,880 |
| Server elapsed (us) | 18,399,948 | 97,551,910 |
| Server RX MiB/s | 0.054348 | 0.051255 |
| Server TX MiB/s (TX window only) | 11.986815 | 13.049958 |
| Client TX MiB/s | 0.054404 | 0.051264 |
| Client RX MiB/s | 0.071295 | 0.067983 |
| Client EAGAIN | 0 | 0 |
| Client errors | 0 | 0 |
| Client stack used/free (bytes) | 2512 / 1584 | 2512 / 1584 |
| Client connect time (us) | 1,002,259 | 10,737,488 |

The user also supplied Zephyr serial output for the 1 MiB run reporting `FULL upload=1048576 download=1048576 elapsed=18466 ms`, `full completed successfully`, and the context close/free diagnostics. No corresponding Zephyr serial completion log was supplied for the 5 MiB run; its client counters are included in the BEN2 server result.

## Interpretation

Both reported Ethernet runs passed with matching client/server byte counters in both directions. The server receive-window throughput decreased by approximately 5.7% between the 1 MiB and 5 MiB runs. The high server TX-window rate measures its brief send window, **not** sustained full-duplex end-to-end throughput. The reported 10 MiB is the sum of 5 MiB sent in each direction.

These are STCP carried over TCP on Ethernet, not STCP-over-UDP or LTE-M. The results do not establish LTE performance, full protocol conformance, or security against active attackers.

## Next steps

Repeat BEN2 TCP and UDP upload, download and full-duplex tests over LTE-M with identical parameters, preserving both endpoints' logs. Investigate the historical STCP-over-UDP download/full-duplex failures reported in `linux-zephyr-lte-2026-11-01.md`. Record exact binary revisions, timestamps and raw logs for reproducibility.
