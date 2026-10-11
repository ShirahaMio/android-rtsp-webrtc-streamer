"""Exercise the real shared library's lifecycle and HTTP adapter on Linux.

This is a host runtime test, not an Android device test.
"""
import ctypes
import json
from pathlib import Path
import os
import socket
import sys
import threading
import urllib.error
import urllib.request

LIB = ctypes.CDLL(sys.argv[1])
LIB.wrs_start.argtypes = [ctypes.c_int]
LIB.wrs_start.restype = ctypes.c_int
LIB.wrs_stop.argtypes = []
LIB.wrs_stop.restype = None
LIB.wrs_is_running.restype = ctypes.c_int
LIB.wrs_last_error.restype = ctypes.c_char_p


def available_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def request(port, path, method="GET", data=None):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method)
    return urllib.request.urlopen(req, timeout=15)


def main():
    assert LIB.wrs_start(80) == -1
    assert b"Port" in LIB.wrs_last_error()
    LIB.wrs_stop()
    # Failed bind must not poison subsequent start/stop cycles.
    with socket.socket() as occupied:
        occupied.bind(("127.0.0.1", 0))
        occupied.listen()
        assert LIB.wrs_start(occupied.getsockname()[1]) == -1
        assert not LIB.wrs_is_running()
    print("PASS invalid port and bind failure recovery", flush=True)
    baseline_threads = None
    for cycle in range(3):
        port = available_port()
        assert LIB.wrs_start(port) == 0, LIB.wrs_last_error()
        assert LIB.wrs_start(port) == 1
        assert LIB.wrs_is_running() == 1
        with request(port, "/health") as response:
            assert json.load(response)["status"] == "ready"
            assert response.headers["Access-Control-Allow-Origin"] == "*"
        with request(port, "/api/getIceServers") as response:
            assert json.load(response)["iceServers"] == []
        with request(port, "/api/call", "OPTIONS") as response:
            assert response.status == 204
        # Non-numeric options may throw in upstream parsing; do not crash the host.
        try:
            with request(port, "/api/call?peerid=invalid", "POST", b"{}") as response:
                assert response.status >= 400
        except urllib.error.HTTPError as error:
            assert error.code in (400, 500)
        with request(port, "/health") as response:
            assert response.status == 200
        LIB.wrs_stop()
        LIB.wrs_stop()
        assert LIB.wrs_is_running() == 0
        with socket.socket() as released:
            released.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            released.bind(("127.0.0.1", port))
        thread_count = len(list(Path("/proc/self/task").iterdir()))
        if baseline_threads is None:
            baseline_threads = thread_count
        else:
            assert thread_count <= baseline_threads, (baseline_threads, thread_count)
        print(f"PASS lifecycle cycle {cycle + 1}, threads after stop={thread_count}", flush=True)
    print("PASS runtime smoke tests", flush=True)


try:
    main()
finally:
    LIB.wrs_stop()
