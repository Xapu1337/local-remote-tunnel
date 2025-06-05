import socket
import subprocess
import threading
import sys
import time

from utils import wait_port

TOKEN = "TESTTOKEN"
DATA = b"hi"


def start_echo_server(port):
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen()

    def handle(conn):
        with conn:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                conn.sendall(data)

    def loop():
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=handle, args=(conn,), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    return srv


def test_retry():
    subprocess.check_call([sys.executable, "generate_cert.py"])

    echo_srv = start_echo_server(9401)

    client_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "client",
        "--server",
        "127.0.0.1:8400",
        "--map",
        "127.0.0.1:9400=127.0.0.1:9401",
        "--token",
        TOKEN,
        "--retries",
        "5",
    ])

    time.sleep(2)

    server_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "server",
        "--cert",
        "cert.pem",
        "--key",
        "key.pem",
        "--listen",
        "127.0.0.1:8400",
        "--token",
        TOKEN,
        "--allow-port",
        "9401",
    ])

    wait_port("127.0.0.1", 8400)

    s = socket.create_connection(("127.0.0.1", 9400))
    s.sendall(DATA)
    resp = s.recv(len(DATA))
    assert resp == DATA
    s.close()

    client_proc.terminate()
    server_proc.terminate()
    echo_srv.close()
