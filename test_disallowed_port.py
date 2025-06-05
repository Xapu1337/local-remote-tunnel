import socket
import subprocess
import threading
import time

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
    echo = start_echo_server(9511)
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
    time.sleep(1)

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
    time.sleep(1)

    s = socket.socket()
    try:
        s.connect(("127.0.0.1", 9512))
        s.sendall(b"test")
        data = s.recv(10)
        if not data:
            print("disallowed port ok")
    except Exception:
        print("disallowed port ok")
    finally:
        s.close()
        client_proc.terminate()
        server_proc.terminate()
        echo.close()


if __name__ == "__main__":
    main()
