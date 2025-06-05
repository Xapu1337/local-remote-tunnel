#!/bin/sh
set -e
openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365 \
  -subj '/CN=local-remote-tunnel'
echo "Generated cert.pem and key.pem"
