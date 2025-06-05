import socket
import subprocess
import threading
import time
import sys

TOKEN = "TESTTOKEN"


def start_kv_server(port):
    db = {}
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen()

    def handler(conn):
        with conn:
            buf = b""
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    parts = line.decode().strip().split(None, 2)
                    if not parts:
                        continue
                    cmd = parts[0].upper()
                    if cmd == "SET" and len(parts) == 3:
                        db[parts[1]] = parts[2]
                        conn.sendall(b"OK\n")
                    elif cmd == "GET" and len(parts) == 2:
                        conn.sendall((db.get(parts[1], "") + "\n").encode())
                    else:
                        conn.sendall(b"ERR\n")

    def accept_loop():
        while True:
            conn, _ = srv.accept()
            threading.Thread(target=handler, args=(conn,), daemon=True).start()

    threading.Thread(target=accept_loop, daemon=True).start()
    return srv


def main():
    subprocess.check_call([sys.executable, "generate_cert.py"])

    kv_srv = start_kv_server(9201)

    server_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "server",
        "--cert",
        "cert.pem",
        "--key",
        "key.pem",
        "--listen",
        "127.0.0.1:8200",
        "--token",
        TOKEN,
        "--allow-port",
        "9201",
    ])
    time.sleep(1)

    client_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "client",
        "--server",
        "127.0.0.1:8200",
        "--map",
        "127.0.0.1:9200=127.0.0.1:9201",
        "--token",
        TOKEN,
    ])
    time.sleep(1)

    s = socket.create_connection(("127.0.0.1", 9200))
    s.sendall(b"SET foo bar\n")
    resp = s.recv(100)
    assert resp == b"OK\n"
    s.sendall(b"GET foo\n")
    resp = s.recv(100)
    assert resp == b"bar\n"
    print("db ok")
    s.close()

    client_proc.terminate()
    server_proc.terminate()
    kv_srv.close()


if __name__ == "__main__":
    main()
