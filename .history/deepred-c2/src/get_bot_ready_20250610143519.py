import itertools
import copy
import yaml
import socket
import psutil
from pathlib import Path
from ipaddress import ip_network, ip_address

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
def get_default_interface_by_ip(ip):
    for iface_name, iface_addrs in psutil.net_if_addrs().items():
        for addr in iface_addrs:
            if addr.family == socket.AF_INET:
                try:
                    if ip_address(ip) in ip_network(f"{addr.address}/{addr.netmask}", strict=False):
                        return iface_name
                except ValueError:
                    continue
    return None

def get_available_interfaces():
    return list(psutil.net_if_addrs().keys())
def get_traffic_generation_configuration():
    config = {}

    # 🌐 WebSocket Server Configuration
    ip = get_user_input(
        "🚀 Enter the IP address of \033[91mDeepRed\033[0m C2 server", 
        default="127.0.0.1", 
        validator=is_valid_ip
    )
    config['server_ip'] = ip

    port = get_user_input(
        "🚀 Enter the port number of the \033[91mDeepRed\033[0m C2 server", 
        default="5000", 
        validator=is_valid_port
    )
    config['server_port'] = int(port)

    # 🔁 Execution mode
    mode = get_user_input(
        "Bot execution in 'auto' or 'manual' mode?", 
        default="auto", 
        validator=lambda x: x.lower() in ["auto", "manual"]
    ).lower()
    config['mode'] = mode

    if mode == "auto":
        rotate_count = get_user_input(
            "How many indivdual flows shoud be generated in auto mode?", 
            default=1, 
            validator=lambda x: x.isdigit() and int(x) > 0
        )
        config['flows_count'] = int(rotate_count)

    # Adversarial perturbation
    adv_required = get_user_input(
        "Is adversarial perturbation required?", 
        default="no", 
        validator=lambda x: x.lower() in ["yes", "no"]
    ).lower()
    config['adversarial'] = adv_required == "yes"

    if config['adversarial']:
        base_dir = Path(__file__).resolve().parent.parent  # go up from src/
        adv_config_path = base_dir / "configs" / "adversarial_perturbation.yam"
        if adv_config_path.exists():
            print(f"Loading adversarial parameters from YAML: {adv_config_path}")
            with adv_config_path.open() as f:
                try:
                    adv_config = yaml.safe_load(f)
                    config['adversarial_config'] = adv_config
                except yaml.YAMLError as e:
                    print("⚠️  Error loading YAML:", e)
                    config['adversarial_config'] = {}
        else:
            print(f"❌ File 'configs/adversarial_perturbation.yaml' not found. Please enter adversarial values manually.")
            if 'adversarial_config' not in config:
                config['adversarial_config'] = {}
            while True:
                    add_more = input("Add adversarial feature with perturbation values? (yes/no) [yes]: ") or "yes"
                    if add_more.lower() != "yes":
                        break

                    feature_name = input("Enter feature name (e.g. src2dst_max_ps): ").strip()
                    value_str = input("Enter values for that feature (comma-separated numbers e.g., 400,200,500): ")
                    try:
                        values = [int(x.strip()) for x in value_str.split(',')]
                        config['adversarial_config'][feature_name] = values

                    except ValueError:
                        print("⚠️  Invalid number format. Skipping entry.")

    # 💾 Traffic capture
    capture = get_user_input(
        "Capture traffic in PCAP?", 
        default="no", 
        validator=lambda x: x.lower() in ["yes", "no"]
    ).lower()
    config['capture_pcap'] = capture == "yes"

    if config['capture_pcap']:
        if config['capture_pcap']:
            available_ifaces = get_available_interfaces()
            default_iface = get_default_interface_by_ip(config['server_ip']) or available_ifaces[0]

            print("Available interfaces:", ", ".join(available_ifaces))
            iface = get_user_input(
                f"Enter the interface to capture on", 
                default=default_iface, 
                validator=lambda x: x in available_ifaces
            )
            config['pcap_interface'] = iface
        
            base_dir = Path(__file__).resolve().parent.parent  # go up from src/
            current_dir = base_dir / "pcap" 
            #current_dir = os.getcwd()
            print(f"Default directory: {current_dir}")
            save_dir = get_user_input(
                "Enter the folder path to save PCAP (leave blank for current)", 
                default=current_dir
            )
            save_path = Path(save_dir).resolve()
            if not save_path.exists():
                print(f"Directory '{save_path}' does not exist. Creating it...")
                save_path.mkdir(parents=True, exist_ok=True)
            config['pcap_save_path'] = str(save_path)

    return config


def generate_atomic_combinations(config):
    """
    Based on values assigned on adversarial feature perturbations, the function try to retrive all possible atomic config covering all combinations.
    Each conf
    """
    list_keys = [k for k, v in config.items() if isinstance(v, list)]
    scalar_keys = [k for k, v in config.items() if not isinstance(v, list)]

    # If no lists, return the config itself as a single combination
    if not list_keys:
        return [config]

    # Extract list values for combinations
    list_values = [config[k] for k in list_keys]

    # Generate cartesian product
    combinations = list(itertools.product(*list_values))

    # Build config dicts
    result = []
    for combo in combinations:
        new_config = copy.deepcopy(config)

        for i, key in enumerate(list_keys):
            new_config[key] = [combo[i]]  # Make it a list with one value

        result.append(new_config)

    return result
"""
bot_config = get_client_configuration()
print("===============Final configuration:===============")
print(bot_config)

underlay_limit = { 'src2dst_packets': 0, 'src2dst_bytes': 0, 'src2dst_max_ps': 0, 'dst2src_packets': 0, 'dst2src_bytes': 0, 'dst2src_max_ps': 0 }


for key, item in bot_config["adversarial_config"].items():
    if key in underlay_limit.keys():
        underlay_limit[key] = item
    else:
        print(f"❌ Adversarial feature has not found")
        break

print(underlay_limit)
"""

underlay_limit = { 'src2dst_packets': 0, 'src2dst_bytes': 0, 'src2dst_max_ps': [1,2,4], 'dst2src_packets': [20,22], 'dst2src_bytes': [7,8,10], 'dst2src_max_ps': 0 }
atomic_config = generate_atomic_combinations(underlay_limit)
for item in atomic_config:
    print(item)
