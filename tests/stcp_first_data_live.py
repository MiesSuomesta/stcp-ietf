#!/usr/bin/env python3
"""Live AF_STCP first-DATA smoke regression. NOT a deterministic HB-01/HB-02 wire fixture.

Requires Linux AF_STCP kernel module and local TCP-carried STCP support.
Unsupported systems fail, rather than being reported as a PASS.
"""
import argparse
import hashlib
import socket
import threading
import traceback
from stcp_kernel_loopback import AF_STCP, STCP_PROTO_TCP, _libc, _address_call, _connect_with_timeout, _accept_with_timeout, receive_exact

def run(host, port, timeout, iterations, size):
    errors = []
    started = threading.Event()

    def payload(i, label):
        seed = hashlib.sha256(f"STCP-HB-{label}-{i}".encode()).digest()
        return (seed * ((size + len(seed) - 1) // len(seed)))[:size]

    def server():
        try:
            with socket.socket(AF_STCP, socket.SOCK_STREAM, STCP_PROTO_TCP) as listener:
                listener.settimeout(timeout)
                _address_call(_libc.bind, listener, host, port)
                listener.listen(8)
                started.set()
                for i in range(iterations):
                    with _accept_with_timeout(listener, timeout) as peer:
                        peer.settimeout(timeout)
                        data = receive_exact(peer, size)
                        assert data == payload(i, "request"), f"request mismatch iteration={i}"
                        peer.sendall(payload(i, "response"))
        except BaseException as exc:
            errors.append(f"server: {exc}\n{traceback.format_exc()}")
            started.set()

    worker = threading.Thread(target=server, daemon=True)
    worker.start()
    if not started.wait(timeout):
        raise TimeoutError("listener not ready")
    for i in range(iterations):
        if errors:
            break
        try:
            with socket.socket(AF_STCP, socket.SOCK_STREAM, STCP_PROTO_TCP) as client:
                client.settimeout(timeout)
                _connect_with_timeout(client, host, port, timeout)
                client.sendall(payload(i, "request"))
                assert receive_exact(client, size) == payload(i, "response"), f"response mismatch iteration={i}"
        except BaseException as exc:
            errors.append(f"client iteration={i}: {exc}\n{traceback.format_exc()}")
            break
    worker.join(timeout + 1)
    if worker.is_alive():
        errors.append("server did not terminate")
    if errors:
        raise RuntimeError("\n".join(errors))
    print(f"PASS: {iterations} live AF_STCP first-DATA exchanges, {size} bytes per direction")
    print("SCOPE: Linux TCP-carried AF_STCP only; not forced same-queue HB-01/HB-02, not Zephyr evidence.")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=19534)
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--iterations", type=int, default=32)
    ap.add_argument("--size", type=int, default=257)
    args = ap.parse_args()
    if args.iterations < 1 or args.size < 1:
        ap.error("iterations and size must be positive")
    run(args.host, args.port, args.timeout, args.iterations, args.size)
