import socket
import subprocess
import threading
import sys

from utils import wait_port

TOKEN = "TESTTOKEN"


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

    def server_thread():
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=handle, args=(conn,), daemon=True).start()

    threading.Thread(target=server_thread, daemon=True).start()
    return srv


def test_disallowed_port():
    echo = start_echo_server(9511)
    subprocess.check_call([sys.executable, "generate_cert.py"])
    server_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "server",
        "--cert",
        "cert.pem",
        "--key",
        "key.pem",
        "--listen",
        "127.0.0.1:9510",
        "--allow-port",
        "80",
        "--token",
        TOKEN,
    ])
    wait_port("127.0.0.1", 9510)

    client_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "client",
        "--server",
        "127.0.0.1:9510",
        "--map",
        "127.0.0.1:9512=127.0.0.1:9511",
        "--token",
        TOKEN,
    ])
    wait_port("127.0.0.1", 9512)

    s = socket.socket()
    try:
        s.connect(("127.0.0.1", 9512))
        s.sendall(b"test")
        data = s.recv(10)
        assert not data
    except Exception:
        pass
    finally:
        s.close()
        client_proc.terminate()
        server_proc.terminate()
        echo.close()
