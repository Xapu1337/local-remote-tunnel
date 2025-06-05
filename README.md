# Local Remote Tunnel

This project provides a simple secure tunneling solution. It allows a client running on a local machine to forward TCP connections to a target host through a remote bridge. All traffic between the client and the server is encrypted using TLS.

## Components

- `tunnel.py` – unified CLI with `server` and `client` subcommands.
- `server.py` and `client.py` remain as thin wrappers but using `tunnel.py` internally.

## Topology

The tunnel uses a star topology. Each client installs the tunneling software
and connects to a central server running on the host machine. The server acts as
a bridge, relaying traffic between remote users and the services exposed by
clients. Connections travel from the remote user to the server and then through
the client's outbound tunnel to the local service.

## Usage

1. Generate a self‑signed certificate for the server. You can use the shell
   script or the Python equivalent depending on your platform:
   ```bash
   ./generate_cert.sh
   # or generate with pure Python (requires `cryptography`)
   pip install cryptography
   python3 generate_cert.py
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

## Guided setup

If you prefer an interactive setup, run `wizard.py` and follow the prompts. It
will help you generate a certificate, start a server or launch a client with the
appropriate parameters.

This is a work in progress.

## Testing

Several helper scripts exercise the tunnel:

```
python3 test_tunnel.py        # 5MB transfer through the tunnel
python3 test_large_transfer.py # 10MB transfer stress test
python3 test_multiport.py     # multiple mappings on one client
python3 test_retry.py         # client reconnection logic
python3 test_webserver.py     # simple HTTP reachability test
python3 test_db.py            # interactive database-style server test
python3 test_invalid_token.py # server rejects wrong token
python3 test_disallowed_port.py # connection fails if port is not allowed

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

Fill in the server address, shared token and one or more mapping lines (in the form `LOCAL=HOST:PORT`) then click **Start**.
