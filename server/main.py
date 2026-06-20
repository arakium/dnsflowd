import json
import socket
import threading
import pyfiglet
from termcolor import colored
import database
import web_ui

HOST     = "0.0.0.0"
LISTENER_PORT = 9999
WEB_PORT = 5000


def handle_client(client_socket: socket.socket, client_address: tuple):
    print(f"[Connection] Router connected from {client_address[0]}:{client_address[1]}")
    buffer = ""
    try:
        while True:
            chunk = client_socket.recv(4096).decode("utf-8", errors="ignore")
            if not chunk:
                break
            buffer += chunk
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    database.insert_data(data)
                    label  = data.get("type", "?")
                    detail = data.get("domain") or data.get("data", "")
                    print(f"[{label:<6}] {data.get('src', '?'):<18} → {detail}")
                except json.JSONDecodeError:
                    print(f"[Error] Bad JSON: {line[:80]}")
    except Exception as e:
        print(f"[Error] {client_address[0]}: {e}")
    finally:
        client_socket.close()
        print(f"[Disconnected] {client_address[0]}")


def main():
    database.setup_db()

    # Bind the socket first — fail early before printing anything
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, LISTENER_PORT))
    server.listen(5)

    # Banner
    print(pyfiglet.figlet_format("dnsflowd", font="big"))
    # print(colored("  by arakium", "green"))
    print(colored(f"  Dashboard  →  http://0.0.0.0:{WEB_PORT}", "cyan"))
    print(colored(f"  Listener   →  {HOST}:{LISTENER_PORT}", "cyan"))
    print()

    # Start web dashboard after banner
    threading.Thread(
        target=web_ui.run_server,
        kwargs={"host": "0.0.0.0", "port": WEB_PORT},
        daemon=True,
    ).start()

    print(f"[Network] Waiting for router connection on port {LISTENER_PORT}...")

    try:
        while True:
            client_sock, client_addr = server.accept()
            threading.Thread(
                target=handle_client,
                args=(client_sock, client_addr),
                daemon=True,
            ).start()
    except KeyboardInterrupt:
        print("\n[Shutdown] Stopped by user.")
    finally:
        server.close()


if __name__ == "__main__":
    main()