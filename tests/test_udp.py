import socket
import subprocess
import threading
import time
import sys

TOKEN = "TESTTOKEN"
DATA = b"ping"


def start_udp_echo(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", port))

    def loop():
        while True:
            data, addr = sock.recvfrom(65535)
            sock.sendto(data, addr)

    threading.Thread(target=loop, daemon=True).start()
    return sock


def test_udp_forward():
    subprocess.check_call([sys.executable, "generate_cert.py"])

    echo_sock = start_udp_echo(9801)

    server_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "server",
        "--cert",
        "cert.pem",
        "--key",
        "key.pem",
        "--listen",
        "127.0.0.1:8600",
        "--token",
        TOKEN,
        "--allow-port",
        "9801",
    ])
    time.sleep(1)

    client_proc = subprocess.Popen([
        "python3",
        "tunnel.py",
        "client",
        "--server",
        "127.0.0.1:8600",
        "--udp-map",
        "127.0.0.1:9800=127.0.0.1:9801",
        "--token",
        TOKEN,
    ])
    time.sleep(1)

    cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cli.sendto(DATA, ("127.0.0.1", 9800))
    cli.settimeout(2)
    resp, _ = cli.recvfrom(1024)
    assert resp == DATA
    cli.close()

    client_proc.terminate()
    server_proc.terminate()
    echo_sock.close()
