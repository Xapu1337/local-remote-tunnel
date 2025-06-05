import argparse
import logging
from rich.logging import RichHandler

from .client import run_client
from .server import run_server


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Remote Tunnel")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
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

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler()],
    )

    args.func(args)


if __name__ == "__main__":
    main()
