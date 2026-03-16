#!/data/data/com.termux/files/usr/bin/bash

echo "Starting One2lvOS..."

cd ~/one2lvos_final

# start API
node api/server.js &

sleep 2

# start reactor
node reactor_core/reactor.js &

sleep 1

# start infinity runtime
cd infinity-glass
./bin/infinity-glass

echo "System ready"
