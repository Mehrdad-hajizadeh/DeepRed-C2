import json
import socket
import netifaces
from pathlib import Path
from contextlib import closing

BASE_DIR = Path(__file__).resolve().parent.parent  # go up from src/
CONFIG_PATH = BASE_DIR / "configs" / "net_config.json"
DEFAULT_PORT = 5000


def get_default_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_available_ips():
    ip_list = []
    for iface in netifaces.interfaces():
        addrs = netifaces.ifaddresses(iface)
        if netifaces.AF_INET in addrs:
            ip_list.extend([addr['addr'] for addr in addrs[netifaces.AF_INET]])
    return ip_list


def is_port_available(port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        return s.connect_ex(('0.0.0.0', port)) != 0


def prompt_ip(default_ip, available_ips):
    while True:
        ip_input = input(f"Enter IP address to bind \033[91mDeepRed\033[0m C2 server [Press Enter to use {default_ip}]: ").strip()
        ip = ip_input if ip_input else default_ip

        if ip in available_ips:
            return ip
        else:
            print(f"❌ IP address {ip} is not valid on this system. Available IPs: {available_ips}")


def prompt_port(default_port):
    while True:
        port_input = input(f"Enter port [Press Enter to use {default_port}]: ").strip()
        try:
            port = int(port_input) if port_input else default_port
            if 1 <= port <= 65535:
                if is_port_available(port):
                    return port
                else:
                    print(f"❌ Port {port} is already in use.")
            else:
                print("❌ Port must be between 1 and 65535.")
        except ValueError:
            print("❌ Invalid input. Please enter a numeric port.")


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}


def save_config(ip, port):
    with open(CONFIG_PATH, "w") as f:
        json.dump({"ip": ip, "port": port}, f, indent=2)


def resolve_settings():
    config = load_config()
    available_ips = get_available_ips()
    default_ip = get_default_ip()

    ip = config.get("ip", default_ip)
    if ip not in available_ips:
        print(f"⚠️ Config IP ({ip}) not found. Reverting to system default.")
        ip = default_ip
    ip = prompt_ip(ip, available_ips)

    port = config.get("port", DEFAULT_PORT)
    port = prompt_port(port)

    save_config(ip, port)
    return ip, port


print(resolve_settings())
