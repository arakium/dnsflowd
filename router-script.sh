#!/bin/sh
# Run this on the OpenWrt Router

SERVER_IP="YOUR_SERVER_IP"
PORT="9999"

echo "Starting DNS capture and streaming to $SERVER_IP:$PORT..."

tcpdump -i br-lan -nn -l ip and udp port 53 | awk -v ip="$SERVER_IP" -v port="$PORT" '
/A\?/ {
    sub(/\.[0-9]+$/, "", $3); sub(/\.[0-9]+:/, "", $5);
    dom = $8; sub(/\.$/, "", dom);
    printf "{\"type\":\"QUERY\",\"src\":\"%s\",\"dst\":\"%s\",\"domain\":\"%s\"}\n", $3, $5, dom
}
/A / {
    sub(/\.[0-9]+$/, "", $3); sub(/\.[0-9]+:/, "", $5);
    match($0, /A .*/);
    ans = substr($0, RSTART+2, RLENGTH-2);
    sub(/ \([0-9]+\)$/, "", ans);

    gsub(/A /, "", ans);

    printf "{\"type\":\"ANSWER\",\"src\":\"%s\",\"dst\":\"%s\",\"data\":\"%s\"}\n", $3, $5, ans
}' | nc $SERVER_IP $PORT