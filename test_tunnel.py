import os
import socket
import subprocess
import threading
import time
import sys

DATA_SIZE = 5 * 1024 * 1024  # 5MB
TOKEN = "TESTTOKEN"


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

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return srv


def main():
    subprocess.check_call([sys.executable, "generate_cert.py"])
    echo_srv = start_echo_server(9001)

    server_proc = subprocess.Popen(
        [
            "python3",
            "tunnel.py",
            "server",
            "--cert",
            "cert.pem",
            "--key",
            "key.pem",
            "--listen",
            "127.0.0.1:8000",
            "--token",
            TOKEN,
            "--allow-port",
            "9001",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    time.sleep(1)

    client_proc = subprocess.Popen(
        ["python3", "tunnel.py", "client", "--server", "127.0.0.1:8000", "--map", "127.0.0.1:9000=127.0.0.1:9001", "--token", TOKEN],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    time.sleep(1)

    data = os.urandom(DATA_SIZE)
    s = socket.create_connection(("127.0.0.1", 9000))
    s.sendall(data)
    received = bytearray()
    while len(received) < len(data):
        chunk = s.recv(4096)
        if not chunk:
            break
        received.extend(chunk)
    s.close()

    assert received == data, "mismatched data"
    print("transfer ok")

    client_proc.terminate()
    server_proc.terminate()
    echo_srv.close()


if __name__ == "__main__":
    main()
