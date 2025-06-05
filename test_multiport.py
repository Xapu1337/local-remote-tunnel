import os
import socket
import subprocess
import threading
import time
import sys

TOKEN = "TESTTOKEN"
DATA = b"hello"


def start_echo_server(port):
    srv = socket.socket()
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


def main():
    subprocess.check_call([sys.executable, "generate_cert.py"])

    echo1 = start_echo_server(9501)
    echo2 = start_echo_server(9502)

    server_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "server",
        "--cert",
        "cert.pem",
        "--key",
        "key.pem",
        "--listen",
        "127.0.0.1:8500",
        "--token",
        TOKEN,
        "--allow-port",
        "9501",
        "--allow-port",
        "9502",
    ])
    time.sleep(1)

    client_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "client",
        "--server",
        "127.0.0.1:8500",
        "--map",
        "127.0.0.1:9600=127.0.0.1:9501",
        "--map",
        "127.0.0.1:9601=127.0.0.1:9502",
        "--token",
        TOKEN,
    ])
    time.sleep(1)

    for lp in (9600, 9601):
        s = socket.create_connection(("127.0.0.1", lp))
        s.sendall(DATA)
        resp = s.recv(len(DATA))
        assert resp == DATA
        s.close()

    print("multi ok")

    client_proc.terminate()
    server_proc.terminate()
    echo1.close()
    echo2.close()


if __name__ == "__main__":
    main()
