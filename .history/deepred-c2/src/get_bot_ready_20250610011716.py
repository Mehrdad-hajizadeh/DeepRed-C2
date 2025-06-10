import os
import yaml
import socket
from pathlib import Path

def get_user_input(prompt, default=None, validator=None):
    while True:
        value = input(f"{prompt} [{default}]: ") or str(default)
        if validator is None or validator(value):
            return value
        print("⚠️  Invalid input. Please try again.")

def is_valid_ip(ip):
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

def is_valid_port(port):
    return port.isdigit() and 0 < int(port) < 65536

def get_client_configuration():
    config = {}

    # 🌐 WebSocket Server Configuration
    ip = get_user_input(
        "📡 Please enter the IP address of \033[91mDeepRed\033[0m C2 server", 
        default="127.0.0.1", 
        validator=is_valid_ip
    )
    config['server_ip'] = ip

    port = get_user_input(
        "📡 Please enter the port number of the WebSocket server", 
        default="8765", 
        validator=is_valid_port
    )
    config['server_port'] = int(port)

    # 🔁 Execution mode
    mode = get_user_input(
        "🔁 Would you like to run the client in 'auto' or 'manual' mode?", 
        default="auto", 
        validator=lambda x: x.lower() in ["auto", "manual"]
    ).lower()
    config['mode'] = mode

    if mode == "auto":
        rotate_count = get_user_input(
            "🔁 How many times should the client auto-rotate?", 
            default=1, 
            validator=lambda x: x.isdigit() and int(x) > 0
        )
        config['rotate_count'] = int(rotate_count)

    # 🧠 Adversarial perturbation
    adv_required = get_user_input(
        "🧠 Is adversarial perturbation required?", 
        default="no", 
        validator=lambda x: x.lower() in ["yes", "no"]
    ).lower()
    config['adversarial'] = adv_required == "yes"

    if config['adversarial']:
        adv_config_path = Path("adversarial_pertubation.yaml")
        if adv_config_path.exists():
            print("🧠 Loading adversarial parameters from YAML...")
            with adv_config_path.open() as f:
                try:
                    adv_config = yaml.safe_load(f)
                    config['adversarial_config'] = adv_config
                except yaml.YAMLError as e:
                    print("⚠️  Error loading YAML:", e)
                    config['adversarial_config'] = {}
        else:
            print("🧠 YAML not found. Please enter adversarial values manually.")
            src2dst_raw = get_user_input(
                "🧠 Enter values for src2dst_max_ps (comma-separated)", 
                default="10,300,400"
            )
            try:
                values = [int(v.strip()) for v in src2dst_raw.split(',')]
                config['adversarial_config'] = {'src2dst_max_ps': values}
            except ValueError:
                print("⚠️  Invalid input. Using default: [10, 300, 400].")
                config['adversarial_config'] = {'src2dst_max_ps': [10, 300, 400]}

    # 💾 Traffic capture
    capture = get_user_input(
        "🛡️  Would you like to capture traffic as a PCAP file?", 
        default="no", 
        validator=lambda x: x.lower() in ["yes", "no"]
    ).lower()
    config['capture_pcap'] = capture == "yes"

    if config['capture_pcap']:
        current_dir = os.getcwd()
        print(f"📁 Current directory: {current_dir}")
        save_dir = get_user_input(
            "💾 Enter the folder path to save PCAP (leave blank for current)", 
            default=current_dir
        )
        save_path = Path(save_dir).resolve()
        if not save_path.exists():
            print(f"📁 Directory '{save_path}' does not exist. Creating it...")
            save_path.mkdir(parents=True, exist_ok=True)
        config['pcap_save_path'] = str(save_path)

    return config


config = get_client_configuration()
print("\nFinal configuration:")
print(config)