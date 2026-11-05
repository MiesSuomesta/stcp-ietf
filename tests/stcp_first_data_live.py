#!/usr/bin/env python3
"""Live Linux AF_STCP first-DATA echo regression.

Client mode targets an ALREADY RUNNING AF_STCP byte-for-byte echo server,
such as utils/stcp_ietf_echo.c on Raspberry Pi. It does not start a server.
Loopback mode retains the original in-process server for comparison.

This is an application-visible live transport test, NOT a deterministic
same-receive-queue HB-01/HB-02 wire fixture.
"""
import argparse
import hashlib
import os
import signal
import socket
import threading
import traceback
from stcp_kernel_loopback import (
    AF_STCP, STCP_PROTO_TCP, _libc, _address_call,
    _accept_with_timeout, receive_exact,
)

def payload(i, size):
    seed = hashlib.sha256(f"STCP-FIRST-DATA-{i}".encode()).digest()
    return (seed * ((size + len(seed) - 1) // len(seed)))[:size]

def run_client(host, port, timeout, iterations, size):
    for i in range(iterations):
        expected = payload(i, size)
        try:
            with socket.socket(AF_STCP, socket.SOCK_STREAM, STCP_PROTO_TCP) as sock:
                # AF_STCP currently completes handshake on blocking connect.
                # Python settimeout() switches the fd to nonblocking and can
                # leave this implementation in EINPROGRESS indefinitely.
                _address_call(_libc.connect, sock, host, port)
                sock.settimeout(timeout)
                sock.sendall(expected)
                actual = receive_exact(sock, size)
                if actual != expected:
                    raise AssertionError(f"echo mismatch: iteration={i}, received={len(actual)} bytes")
        except BaseException as exc:
            raise RuntimeError(
                f"FAIL: iteration={i + 1}/{iterations}, target={host}:{port}, "
                f"stage=connect/send/recv, error={exc}"
            ) from exc
        print(f"PASS {i + 1}/{iterations}: {size}-byte encrypted STCP echo", flush=True)
    print(f"PASS: {iterations}/{iterations} Linux AF_STCP -> {host}:{port} echo exchanges")
    print("LIMITATION: no deterministic handshake/DATA coalescing; HB-01/HB-02 NOT verified.")

def run_loopback(host, port, timeout, iterations, size):
    errors = []
    ready = threading.Event()

    def server():
        try:
            with socket.socket(AF_STCP, socket.SOCK_STREAM, STCP_PROTO_TCP) as listener:
                listener.settimeout(timeout)
                _address_call(_libc.bind, listener, host, port)
                listener.listen(8)
                ready.set()
                for i in range(iterations):
                    with _accept_with_timeout(listener, timeout) as peer:
                        peer.settimeout(timeout)
                        expected = payload(i, size)
                        actual = receive_exact(peer, size)
                        if actual != expected:
                            raise AssertionError(f"request mismatch iteration={i}")
                        peer.sendall(actual)
        except BaseException as exc:
            errors.append(f"server: {exc}\n{traceback.format_exc()}")
            ready.set()

    worker = threading.Thread(target=server, daemon=True)
    worker.start()
    if not ready.wait(timeout):
        raise TimeoutError("loopback listener not ready")
    if not errors:
        try:
            run_client(host, port, timeout, iterations, size)
        except BaseException as exc:
            errors.append(f"client: {exc}\n{traceback.format_exc()}")
    worker.join(timeout + 1)
    if worker.is_alive():
        errors.append("loopback server did not terminate")
    if errors:
        raise RuntimeError("\n".join(errors))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("client", "loopback"), default="client")
    ap.add_argument("--host", default="192.168.1.242", help="remote echo server in client mode")
    ap.add_argument("--port", type=int, default=19000)
    ap.add_argument("--timeout", type=float, default=15.0, help="per-operation socket timeout after blocking connect; use external timeout(1) to bound connect")
    ap.add_argument("--iterations", type=int, default=32)
    ap.add_argument("--size", type=int, default=257)
    args = ap.parse_args()
    if args.iterations < 1 or args.size < 1 or args.timeout <= 0 or not 1 <= args.port <= 65535:
        ap.error("iterations, size, timeout and port must be positive and port <= 65535")
    if args.mode == "loopback" and args.host != "127.0.0.1":
        ap.error("loopback mode requires --host 127.0.0.1")
    if args.mode == "client":
        run_client(args.host, args.port, args.timeout, args.iterations, args.size)
    else:
        run_loopback(args.host, args.port, args.timeout, args.iterations, args.size)
