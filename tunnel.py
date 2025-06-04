#!/usr/bin/env python3
"""Unified CLI for running the tunnel client or server."""

import argparse
import asyncio
import ssl
import time
from collections import defaultdict, deque


# --------------------------- Client functionality ---------------------------
async def handle_local(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    server: str,
    target: str,
    token: str,
    ca: str | None,
    retries: int,
):
    attempt = 0
    while True:
        try:
            server_host, server_port = server.split(":")
            ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            if ca:
                ssl_ctx.load_verify_locations(ca)
            else:
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE
            remote_reader, remote_writer = await asyncio.open_connection(
                server_host, int(server_port), ssl=ssl_ctx
            )
            connect_line = f"CONNECT {token} {target}\n".encode()
            remote_writer.write(connect_line)
            await remote_writer.drain()
            break
        except Exception:
            attempt += 1
            if attempt > retries:
                writer.close()
                await writer.wait_closed()
                return
            await asyncio.sleep(min(2 ** attempt, 5))

    async def pipe(reader1, writer1):
        try:
            while data := await reader1.read(4096):
                writer1.write(data)
                await writer1.drain()
        finally:
            writer1.close()

    await asyncio.gather(
        pipe(reader, remote_writer),
        pipe(remote_reader, writer),
    )


def run_client(args):
    if not args.map:
        raise SystemExit("At least one --map must be provided")

    loop = asyncio.get_event_loop()
    servers = []
    for m in args.map:
        local, target = m.split("=", 1)
        host, port = local.split(":")
        srv_coro = asyncio.start_server(
            lambda r, w, targ=target: handle_local(
                r,
                w,
                args.server,
                targ,
                args.token,
                args.ca,
                args.retries,
            ),
            host,
            int(port),
        )
        srv = loop.run_until_complete(srv_coro)
        servers.append(srv)
        addr = ", ".join(str(sock.getsockname()) for sock in srv.sockets)
        print(f"Forwarding {addr} -> {target}")

    try:
        loop.run_forever()
    finally:
        for srv in servers:
            srv.close()
            loop.run_until_complete(srv.wait_closed())


# --------------------------- Server functionality ---------------------------
class RateLimiter:
    """Simple per-IP rate limiter to avoid abuse."""

    def __init__(self, limit_per_minute: int = 60):
        self.limit = limit_per_minute
        self.connections: defaultdict[str, deque] = defaultdict(deque)

    def allowed(self, ip: str) -> bool:
        now = time.time()
        q = self.connections[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    token: str,
    limiter: RateLimiter,
    allowed_ports: set[int] | None,
):
    peer = writer.get_extra_info("peername")[0]
    if not limiter.allowed(peer):
        writer.close()
        await writer.wait_closed()
        return
    try:
        line = await reader.readline()
        parts = line.decode().strip().split()
        if len(parts) != 3 or parts[0] != "CONNECT" or parts[1] != token:
            raise ValueError("invalid header")
        host, port_str = parts[2].split(":")
        port = int(port_str)
        if allowed_ports is not None and port not in allowed_ports:
            raise ValueError("port not allowed")
    except Exception:
        writer.close()
        await writer.wait_closed()
        return

    try:
        remote_reader, remote_writer = await asyncio.open_connection(host, port)
    except Exception:
        writer.close()
        await writer.wait_closed()
        return

    async def pipe(reader1, writer1):
        try:
            while data := await reader1.read(4096):
                writer1.write(data)
                await writer1.drain()
        finally:
            writer1.close()

    await asyncio.gather(
        pipe(reader, remote_writer),
        pipe(remote_reader, writer),
    )


def run_server(args):
    if not args.listen:
        args.listen = ["0.0.0.0:8000"]

    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(args.cert, args.key)
    limiter = RateLimiter(args.rate)
    allowed_ports = {int(p) for p in args.allow_port} if args.allow_port else None

    loop = asyncio.get_event_loop()
    servers = []

    for listen in args.listen:
        host, port = listen.split(":")

        async def handler(reader, writer):
            await handle_client(reader, writer, args.token, limiter, allowed_ports)

        server_coro = asyncio.start_server(handler, host, int(port), ssl=ssl_ctx)
        srv = loop.run_until_complete(server_coro)
        servers.append(srv)
        addr = ", ".join(str(sock.getsockname()) for sock in srv.sockets)
        print(f"Serving on {addr}")

    try:
        loop.run_forever()
    finally:
        for srv in servers:
            srv.close()
            loop.run_until_complete(srv.wait_closed())


# --------------------------- CLI entry point ---------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Local Remote Tunnel")
    sub = parser.add_subparsers(dest="cmd", required=True)

    serv = sub.add_parser("server", help="Run tunnel server")
    serv.add_argument("--cert", required=True, help="Path to TLS certificate")
    serv.add_argument("--key", required=True, help="Path to TLS key")
    serv.add_argument(
        "--listen",
        action="append",
        metavar="ADDR",
        help="Address to listen on (can be given multiple times)",
    )
    serv.add_argument("--token", required=True, help="Shared secret token")
    serv.add_argument("--rate", type=int, default=60, help="Max connections per minute per IP")
    serv.add_argument(
        "--allow-port",
        action="append",
        metavar="PORT",
        help="Restrict forwarding to these destination ports (can be repeated)",
    )
    serv.set_defaults(func=run_server)

    cli = sub.add_parser("client", help="Run tunnel client")
    cli.add_argument("--server", required=True, help="Server address")
    cli.add_argument(
        "--map",
        action="append",
        metavar="LOCAL=TARGET",
        help="Local listen address mapped to target host:port",
    )
    cli.add_argument("--token", required=True, help="Shared secret token")
    cli.add_argument("--ca", help="CA certificate for server")
    cli.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Number of reconnect attempts if the server is unreachable",
    )
    cli.set_defaults(func=run_client)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
