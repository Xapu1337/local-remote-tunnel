import os
import socket
import subprocess
import threading
import sys

from utils import wait_port

TOKEN = "TESTTOKEN"
SIZE = 10 * 1024 * 1024  # 10MB


def start_echo_server(port):
    def handler(conn):
        with conn:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                conn.sendall(data)

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen()

    def run():
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=handler, args=(conn,), daemon=True).start()

    threading.Thread(target=run, daemon=True).start()
    return srv


def test_large_transfer():
    subprocess.check_call([sys.executable, "generate_cert.py"])

    echo_srv = start_echo_server(9301)

    server_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "server",
        "--cert",
        "cert.pem",
        "--key",
        "key.pem",
        "--listen",
        "127.0.0.1:8300",
        "--token",
        TOKEN,
        "--allow-port",
        "9301",
    ])
    wait_port("127.0.0.1", 8300)

    client_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "client",
        "--server",
        "127.0.0.1:8300",
        "--map",
        "127.0.0.1:9300=127.0.0.1:9301",
        "--token",
        TOKEN,
    ])
    wait_port("127.0.0.1", 9300)

    data = os.urandom(SIZE)
    s = socket.create_connection(("127.0.0.1", 9300))
    s.sendall(data)
    received = bytearray()
    while len(received) < len(data):
        chunk = s.recv(4096)
        if not chunk:
            break
        received.extend(chunk)
    s.close()
    assert received == data

    client_proc.terminate()
    server_proc.terminate()
    echo_srv.close()
