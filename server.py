#!/usr/bin/env python3
"""Thin wrapper executing `tunnel.py server` for backward compatibility."""

from tunnel import run_server, main as tunnel_main


def main() -> None:
    tunnel_main()


if __name__ == "__main__":
    main()
