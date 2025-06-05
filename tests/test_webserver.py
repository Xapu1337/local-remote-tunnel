import http.server
import socket
import subprocess
import threading
import urllib.request
import sys

from utils import wait_port

TOKEN = "TESTTOKEN"


def start_http_server(port):
    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.HTTPServer(("127.0.0.1", port), handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def test_webserver():
    subprocess.check_call([sys.executable, "generate_cert.py"])

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
    wait_port("127.0.0.1", 8100)

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
    wait_port("127.0.0.1", 9100)

    resp = urllib.request.urlopen("http://127.0.0.1:9100/")
    assert resp.status == 200
    data = resp.read(100)
    assert data

    client_proc.terminate()
    server_proc.terminate()
    http_srv.shutdown()
