#!/usr/bin/env python3
"""Live AF_STCP TCP-carrier loopback smoke test.

Runs actual Linux kernel AF_STCP send/recv (and therefore its negotiated
session protection path), NOT a byte-for-byte crypto known-answer test.
Requires a loaded STCP kernel module and a functioning AF_STCP TCP carrier.
Usage: python3 tests/stcp_kernel_loopback.py --port 19533
No test is silently skipped: unsupported AF_STCP, timeouts and short reads fail.
"""
import argparse
import ctypes
import os
import struct
import socket
import threading
import traceback

AF_STCP = 45
STCP_PROTO_TCP = 253


# AF_STCP sockets accept IPv4 sockaddr_in addresses. CPython's socket.bind
# rejects address conversion for the unknown AF_STCP family, so use libc.
_libc = ctypes.CDLL(None, use_errno=True)
_libc.bind.argtypes = (ctypes.c_int, ctypes.c_void_p, ctypes.c_uint)
_libc.bind.restype = ctypes.c_int
_libc.connect.argtypes = (ctypes.c_int, ctypes.c_void_p, ctypes.c_uint)
_libc.connect.restype = ctypes.c_int

def _ipv4_sockaddr(host, port):
    if not (0 <= port <= 65535):
        raise ValueError("port must be 0..65535")
    # sin_family is host-endian; sin_port and sin_addr are network-endian.
    raw = struct.pack("=H", socket.AF_INET) + struct.pack("!H", port) + socket.inet_aton(host) + bytes(8)
    return ctypes.create_string_buffer(raw)

def _address_call(operation, sock, host, port):
    addr = _ipv4_sockaddr(host, port)
    if operation(sock.fileno(), addr, len(addr.raw) - 1) != 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))

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
                _address_call(_libc.bind, listener, host, port)
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
                _address_call(_libc.connect, client, host, port)
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
