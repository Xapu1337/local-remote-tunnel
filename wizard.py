#!/usr/bin/env python3
"""Interactive wizard to set up and run the tunnel."""
import os
import subprocess


def run_server():
    port = input("Listen address [0.0.0.0:8000]: ").strip() or "0.0.0.0:8000"
    token = input("Shared token: ").strip()
    allow = input("Allowed destination ports (comma separated, blank for all): ")
    allow_args = []
    if allow:
        for p in allow.split(','):
            p = p.strip()
            if p:
                allow_args += ["--allow-port", p]
    cert = input("TLS certificate path [cert.pem]: ").strip() or "cert.pem"
    key = input("TLS key path [key.pem]: ").strip() or "key.pem"
    if not os.path.exists(cert) or not os.path.exists(key):
        print("Generating self-signed certificate...")
        subprocess.check_call(["./generate_cert.sh"])
    cmd = ["python3", "tunnel.py", "server", "--cert", cert, "--key", key,
           "--listen", port, "--token", token] + allow_args
    print("Running:", " ".join(cmd))
    subprocess.call(cmd)


def run_client():
    server = input("Server address [host:port]: ").strip()
    token = input("Shared token: ").strip()
    mappings = []
    while True:
        m = input("Mapping LOCAL=HOST:PORT (blank to finish): ").strip()
        if not m:
            break
        mappings += ["--map", m]
    ca = input("CA certificate path (optional): ").strip()
    retries = input("Reconnect attempts [3]: ").strip() or "3"
    cmd = ["python3", "tunnel.py", "client", "--server", server, "--token", token,
           "--retries", retries] + mappings
    if ca:
        cmd += ["--ca", ca]
    print("Running:", " ".join(cmd))
    subprocess.call(cmd)


def main() -> None:
    print("Local Remote Tunnel setup wizard")
    mode = input("Select mode (server/client): ").strip().lower()
    if mode.startswith('s'):
        run_server()
    elif mode.startswith('c'):
        run_client()
    else:
        print("Unknown mode")


if __name__ == "__main__":
    main()
