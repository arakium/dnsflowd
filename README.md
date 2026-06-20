# dnsflowd

A small DNS traffic monitor and blocklist dashboard.

It has two parts:
- a Python server that receives DNS event logs, stores them in SQLite, and serves a web dashboard
- an OpenWrt router script that streams DNS query/answer events to the server

## Requirements

- Python 3
- Packages from `requirements.txt`
- OpenWrt router tools for the capture script: `tcpdump` and `nc`

## Install

```bash
pip install -r requirements.txt
```

## Run the server

From the `server/` directory:

```bash
cd server
python main.py
```

This starts:
- the listener on port `9999`
- the web dashboard on `http://localhost:5000`

The SQLite database is created automatically if it does not exist.

## Router setup

Edit `router-script.sh` and set:
- `SERVER_IP` to your server's IP address

Then run it on the router:

```bash
sh router-script.sh
```

## Notes

- The dashboard shows recent DNS traffic, stats, and top talkers.
- The blocklist can be managed from the web UI.
- SQLite data is stored in `server/dns_traffic.db` when the server is run from `server/`.

