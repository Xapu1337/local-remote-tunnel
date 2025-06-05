import asyncio
import ssl
import logging
import time
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

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

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                        token: str, limiter: RateLimiter,
                        allowed_ports: set[int] | None):
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


def run_server(args) -> None:
    if not args.listen:
        args.listen = ["0.0.0.0:8000"]

    ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_ctx.load_cert_chain(args.cert, args.key)
    limiter = RateLimiter(args.rate)
    allowed_ports = {int(p) for p in args.allow_port} if args.allow_port else None

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    servers = []

    for listen in args.listen:
        host, port = listen.split(":")

        async def handler(reader, writer):
            await handle_client(reader, writer, args.token, limiter, allowed_ports)

        server_coro = asyncio.start_server(handler, host, int(port), ssl=ssl_ctx)
        srv = loop.run_until_complete(server_coro)
        servers.append(srv)
        addr = ", ".join(str(sock.getsockname()) for sock in srv.sockets)
        logger.info("Serving on %s", addr)

    try:
        loop.run_forever()
    finally:
        for srv in servers:
            srv.close()
            loop.run_until_complete(srv.wait_closed())
