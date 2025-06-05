import asyncio
import ssl
import socket
import logging

logger = logging.getLogger(__name__)

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
            logger.debug("Connecting to %s (%s) attempt %d", server, target, attempt + 1)
            remote_reader, remote_writer = await asyncio.open_connection(
                server_host, int(server_port), ssl=ssl_ctx
            )
            connect_line = f"CONNECT {token} {target}\n".encode()
            remote_writer.write(connect_line)
            await remote_writer.drain()
            logger.info("Connected to server %s for %s", server, target)
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


async def handle_udp(
    local_host: str,
    local_port: int,
    server: str,
    target: str,
    token: str,
    ca: str | None,
    retries: int,
):
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((local_host, local_port))
    sock.setblocking(False)

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
            logger.debug(
                "Connecting UDP to %s (%s) attempt %d", server, target, attempt + 1
            )
            reader, writer = await asyncio.open_connection(
                server_host, int(server_port), ssl=ssl_ctx
            )
            writer.write(f"UDP {token} {target}\n".encode())
            await writer.drain()
            logger.info("UDP connected to server %s for %s", server, target)
            break
        except Exception:
            attempt += 1
            if attempt > retries:
                sock.close()
                return
            await asyncio.sleep(min(2 ** attempt, 5))

    peer = None

    async def to_server():
        nonlocal peer
        while True:
            data, addr = await loop.sock_recvfrom(sock, 65535)
            peer = addr
            writer.write(len(data).to_bytes(2, "big") + data)
            await writer.drain()

    async def from_server():
        while True:
            len_data = await reader.readexactly(2)
            length = int.from_bytes(len_data, "big")
            data = await reader.readexactly(length)
            if peer:
                await loop.sock_sendto(sock, data, peer)

    await asyncio.gather(to_server(), from_server())


def run_client(args) -> None:
    if not args.map and not args.udp_map:
        raise SystemExit("At least one --map or --udp-map must be provided")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    servers = []
    for m in args.map or []:
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
        logger.info("Forwarding %s -> %s", addr, target)

    for m in args.udp_map or []:
        local, target = m.split("=", 1)
        host, port = local.split(":")
        loop.create_task(
            handle_udp(
                host,
                int(port),
                args.server,
                target,
                args.token,
                args.ca,
                args.retries,
            )
        )
        logger.info("UDP forwarding %s -> %s", local, target)

    try:
        loop.run_forever()
    finally:
        for srv in servers:
            srv.close()
            loop.run_until_complete(srv.wait_closed())
