import os
import subprocess
import database

ROUTER_IP: str = "192.168.1.1"
ROUTER_USER: str = "root"
REMOTE_TARGET: str = f"{ROUTER_USER}@{ROUTER_IP}"

PRIVATE_KEY_PATH: str = os.path.expanduser(r"~/.ssh/id_rsa")

BLOCKLIST_FILE: str = r"/etc/dnsmasq.d/blocklist.conf"


def sync_blocklist_to_router(force_restart: bool = False) -> bool:
    """
    Fetches the full blocklist state from SQLite, writes it to OpenWrt.
    Uses 'reload' for quick blocking, or a detached 'restart' to kill the dynamic RAM cache.
    """
    blocked_domains = database.get_all_blocked_domains()

    config_lines = [f"address=/{domain.strip().lower()}/\n" for domain in blocked_domains]
    payload = "".join(config_lines)

    base_ssh = [
        "ssh",
        "-i", PRIVATE_KEY_PATH,
        "-o", "StrictHostKeyChecking=accept-new",
        REMOTE_TARGET
    ]

    write_process = subprocess.run(
        base_ssh + [f"cat > {BLOCKLIST_FILE}"],
        input=payload,
        text=True,
        capture_output=True,
        timeout=5
    )

    if write_process.returncode != 0:
        print(f"[Blocker Error] Failed writing configurations payload: {write_process.stderr}")
        return False

    if force_restart:
        # Run restart in the background and return immediately so SSH socket doesn't hang
        reload_process = subprocess.run(
            base_ssh + ["/etc/init.d/dnsmasq restart > /dev/null 2>&1 &"],
            capture_output=True,
            timeout=5
        )
    else:
        reload_process = subprocess.run(
            base_ssh + ["/etc/init.d/dnsmasq", "reload"],
            capture_output=True,
            timeout=5
        )

    return reload_process.returncode == 0


def block_domain(domain: str) -> bool:
    """Adds a target rule to database records and forces a clean router refresh."""
    clean_domain = domain.strip().lower()

    if not clean_domain or "." not in clean_domain:
        print(f"[Blocker Warning] Ignored invalid domain input: '{domain}'")
        return False

    database.add_to_blocklist(clean_domain)
    return sync_blocklist_to_router(force_restart=True)


def unblock_domain(domain: str) -> bool:
    """Removes a target rule from database records and forces a clean router refresh."""
    clean_domain = domain.strip().lower()
    if not clean_domain:
        return False

    database.remove_from_blocklist(clean_domain)
    return sync_blocklist_to_router(force_restart=True)
