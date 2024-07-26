#!/bin/sh

# Start aria2c in the background
echo "======================================="
echo "             Starting aria2c           "
echo "======================================="
aria2c --enable-rpc --rpc-listen-all=false --rpc-listen-port=6800 \
  --max-connection-per-server=10 --rpc-max-request-size=1024M \
  --seed-time=0.01 --min-split-size=10M --follow-torrent=mem --split=10 \
  --daemon=true --allow-overwrite=true --max-overall-download-limit=0 \
  --max-overall-upload-limit=1K --max-concurrent-downloads=5

#Sleep for 1 seconds
sleep 1

# Start your Python application here
echo "======================================="
echo "             Starting app           "
echo "======================================="
python3 app.py
