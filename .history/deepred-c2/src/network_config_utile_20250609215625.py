import json
import socket
import netifaces
from pathlib import Path
from contextlib import closing

CONFIG_PATH = Path("config.json")
DEFAULT_PORT = 8765


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


def confirm_or_change(prompt_val, prompt_msg):
    response = input(f"{prompt_msg} [Y/n to change]: ").strip().lower()
    if response == 'n':
        return input("Enter new value: ").strip()
    return prompt_val


def prompt_ip(default_ip):
    return confirm_or_change(default_ip, f"Use default IP address {default_ip}?")


def prompt_port(default_port):
    while True:
        port = int(confirm_or_change(str(default_port), f"Use default port {default_port}?"))
        if is_port_available(port):
            return port
        print(f"⚠️ Port {port} is already in use. Try another.")


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
        print(f"⚠️ IP {ip} not found on system. Using default.")
        ip = default_ip
    ip = prompt_ip(ip)

    port = config.get("port", DEFAULT_PORT)
    port = prompt_port(port)

    save_config(ip, port)
    return ip, port

print(resolve_settings())