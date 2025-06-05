import socket
import subprocess
import threading
import time
import sys

TOKEN = "TESTTOKEN"


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

    def server_thread():
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=handle, args=(conn,), daemon=True).start()

    threading.Thread(target=server_thread, daemon=True).start()
    return srv


def main():
    echo = start_echo_server(9501)
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
        "127.0.0.1:9500",
        "--allow-port",
        "9501",
        "--token",
        TOKEN,
    ])
    time.sleep(1)

    client_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "client",
        "--server",
        "127.0.0.1:9500",
        "--map",
        "127.0.0.1:9502=127.0.0.1:9501",
        "--token",
        "WRONG",
    ])
    time.sleep(1)

    s = socket.socket()
    try:
        s.connect(("127.0.0.1", 9502))
        s.sendall(b"test")
        data = s.recv(10)
        if not data:
            print("invalid token ok")
    except Exception:
        print("invalid token ok")
    finally:
        s.close()
        client_proc.terminate()
        server_proc.terminate()
        echo.close()


if __name__ == "__main__":
    main()
