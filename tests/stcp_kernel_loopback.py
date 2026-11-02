#!/usr/bin/env python3
"""Live AF_STCP TCP-carrier loopback smoke test.

Runs actual Linux kernel AF_STCP send/recv (and therefore its negotiated
session protection path), NOT a byte-for-byte crypto known-answer test.
Requires a loaded STCP kernel module and a functioning AF_STCP TCP carrier.
Usage: python3 tests/stcp_kernel_loopback.py --port 19533
No test is silently skipped: unsupported AF_STCP, timeouts and short reads fail.
"""
import argparse
import os
import socket
import threading
import traceback

AF_STCP = 45
STCP_PROTO_TCP = 253

def receive_exact(sock, count):
    result = bytearray()
    while len(result) < count:
        part = sock.recv(count - len(result))
        if not part:
            raise AssertionError(f"Unexpected EOF after {len(result)}/{count} bytes")
        result.extend(part)
    return bytes(result)

def run(host, port, timeout):
    payload = b"STCP-IETF-live-kernel-loopback\x00" + bytes(range(256)) * 4
    response = b"STCP-IETF-live-reply\x00" + bytes(range(255, -1, -1))
    errors = []
    ready = threading.Event()

    def server():
        try:
            with socket.socket(AF_STCP, socket.SOCK_STREAM, STCP_PROTO_TCP) as listener:
                listener.settimeout(timeout)
                listener.bind((host, port))
                listener.listen(1)
                ready.set()
                with listener.accept()[0] as peer:
                    peer.settimeout(timeout)
                    received = receive_exact(peer, len(payload))
                    if received != payload:
                        raise AssertionError("Server received corrupted data")
                    peer.sendall(response)
        except BaseException as exc:
            errors.append(("server", exc, traceback.format_exc()))
            ready.set()

    thread = threading.Thread(target=server, daemon=True)
    thread.start()
    if not ready.wait(timeout):
        raise TimeoutError("Server did not become ready")
    if not errors:
        try:
            with socket.socket(AF_STCP, socket.SOCK_STREAM, STCP_PROTO_TCP) as client:
                client.settimeout(timeout)
                client.connect((host, port))
                client.sendall(payload)
                if receive_exact(client, len(response)) != response:
                    raise AssertionError("Client received corrupted data")
        except BaseException as exc:
            errors.append(("client", exc, traceback.format_exc()))
    thread.join(timeout + 1)
    if thread.is_alive():
        raise TimeoutError("Server thread did not finish")
    if errors:
        raise RuntimeError("\n".join(f"{who}: {exc}\n{tb}" for who, exc, tb in errors))
    print(f"PASS: AF_STCP={AF_STCP} TCP selector={STCP_PROTO_TCP}, "
          f"client->server={len(payload)} bytes, server->client={len(response)} bytes")
    print("LIMITATION: This checks application-visible kernel socket transport, "
          "not wire captures, cryptographic vector equivalence or Zephyr interoperability.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=19533)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    run(args.host, args.port, args.timeout)
