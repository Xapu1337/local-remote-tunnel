# Local Remote Tunnel

This project provides a simple secure tunneling solution. It allows a client running on a local machine to forward TCP connections to a target host through a remote bridge. All traffic between the client and the server is encrypted using TLS.

## Components

- `tunnel.py` – unified CLI with `server` and `client` subcommands.
- `server.py` and `client.py` remain as thin wrappers but using `tunnel.py` internally.

## Usage

1. Generate a self‑signed certificate for the server:
   ```bash
   ./generate_cert.sh
   ```
2. Start the server on the bridge host (you can listen on multiple ports):
   ```bash
   python3 tunnel.py server --cert cert.pem --key key.pem \
       --listen 0.0.0.0:8000 --listen 0.0.0.0:9000 \
       --allow-port 80 --allow-port 22 --token SECRET
   # --allow-port restricts which destination ports clients may access
   ```
3. Start the client on the machine hosting the service you want to expose. Each
   `--map` value forwards a local address to a remote target via the server:
   ```bash
   python3 tunnel.py client --server bridge.example.com:8000 \
       --map 127.0.0.1:8080=localhost:80 \
       --map 127.0.0.1:2222=localhost:22 --token SECRET \
       --retries 5
   # --retries controls how many times the client will try to reconnect if the
   # server is temporarily unreachable
   ```
4. Remote users can reach the forwarded services by connecting to the server's
   listening ports. Each connection must send the shared token first, followed by
   the target host and port (handled automatically by the client) to prevent
   abuse.

5. To run the server continuously, create a systemd unit pointing at the `server` subcommand. A basic example is provided in `tunnel.service`.

This is a work in progress.

## Testing

Two helper scripts exercise the tunnel:

```
python3 test_tunnel.py      # bulk data transfer test
python3 test_webserver.py   # simple HTTP reachability test
```

## Windows GUI

For convenience Windows users can launch `windows_gui.py` which provides a
minimal interface for starting the client and viewing its log output. Run:

```bash
python windows_gui.py
```

Fill in the server address, shared token and one or more mapping lines (in the
form `LOCAL=HOST:PORT`) then click **Start**.

