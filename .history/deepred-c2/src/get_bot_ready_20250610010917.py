import os
import yaml
from pathlib import Path

def get_user_input(prompt, default=None, validator=None):
    while True:
        raw = input(f"{prompt} [{default}]: ") or str(default)
        if validator is None or validator(raw):
            return raw
        print("❌ Invalid input. Please try again.")

def get_client_configuration():
    config = {}

    # 1. Auto/manual mode
    mode = get_user_input(
        "Do you want to run the client in auto or manual mode?", 
        default="auto", 
        validator=lambda x: x.lower() in ["auto", "manual"]
    ).lower()
    config['mode'] = mode

    if mode == "auto":
        rotate_count = get_user_input(
            "How many flows shoudl be generated in the auto mode?", 
            default=1, 
            validator=lambda x: x.isdigit() and int(x) > 0
        )
        config['rotate_count'] = int(rotate_count)

    # 2. Adversarial perturbation
    adv_required = get_user_input(
        "Is adversarial perturbation required?", 
        default="no", 
        validator=lambda x: x.lower() in ["yes", "no"]
    ).lower()
    config['adversarial'] = adv_required == "yes"

    if config['adversarial']:
        adv_config_path = Path("adversarial_pertubation.yaml")
        if adv_config_path.exists():
            print("Loading adversarial parameters from YAML...")
            with adv_config_path.open() as f:
                try:
                    adv_config = yaml.safe_load(f)
                    config['adversarial_config'] = adv_config
                except yaml.YAMLError as e:
                    print("❌ Error loading YAML:", e)
                    config['adversarial_config'] = {}
        else:
            print("YAML config not found. Please enter values manually.")
            src2dst_raw = get_user_input(
                "Enter values for src2dst_max_ps (comma-separated)", 
                default="800,300,400"
            )
            try:
                src2dst_values = [int(v.strip()) for v in src2dst_raw.split(',')]
                config['adversarial_config'] = {'src2dst_max_ps': src2dst_values}
            except ValueError:
                print("❌ Invalid input for src2dst_max_ps. Using default [10, 300, 400].")
                config['adversarial_config'] = {'src2dst_max_ps': [800, 300, 400]}

    # 5. Capture traffic?
    capture = get_user_input(
        "Do you want to capture traffic as a pcap file?", 
        default="no", 
        validator=lambda x: x.lower() in ["yes", "no"]
    ).lower()
    config['capture_pcap'] = capture == "yes"

    if config['capture_pcap']:
        current_dir = os.getcwd()
        print(f"Current directory: {current_dir}")
        save_dir = get_user_input(
            "Enter folder to save pcap (leave empty to use current folder)", 
            default=current_dir
        )
        save_path = Path(save_dir).resolve()
        if not save_path.exists():
            print(f"Directory '{save_path}' does not exist. Creating it...")
            save_path.mkdir(parents=True, exist_ok=True)
        config['pcap_save_path'] = str(save_path)

    return config

config = get_client_configuration()
print("\nFinal configuration:")
print(config)