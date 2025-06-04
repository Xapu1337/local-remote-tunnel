import http.server
import socket
import subprocess
import threading
import time
import urllib.request

TOKEN = "TESTTOKEN"


def start_http_server(port):
    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.HTTPServer(("127.0.0.1", port), handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main():
    subprocess.check_call(["./generate_cert.sh"])

    http_srv = start_http_server(9101)

    server_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "server",
        "--cert",
        "cert.pem",
        "--key",
        "key.pem",
        "--listen",
        "127.0.0.1:8100",
        "--token",
        TOKEN,
        "--allow-port",
        "9101",
    ])
    time.sleep(1)

    client_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "client",
        "--server",
        "127.0.0.1:8100",
        "--map",
        "127.0.0.1:9100=127.0.0.1:9101",
        "--token",
        TOKEN,
    ])
    time.sleep(1)

    resp = urllib.request.urlopen("http://127.0.0.1:9100/")
    assert resp.status == 200
    data = resp.read(100)
    assert data
    print("web ok")

    client_proc.terminate()
    server_proc.terminate()
    http_srv.shutdown()


if __name__ == "__main__":
    main()
