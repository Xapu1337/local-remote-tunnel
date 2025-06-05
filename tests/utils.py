import socket
import time

def wait_port(host: str, port: int, timeout: float = 5.0) -> None:
    """Block until a TCP port starts accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket() as sock:
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError(f"Port {host}:{port} not ready after {timeout}s")
