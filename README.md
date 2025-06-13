# 🧠 DeepRed Command and Control (C2)

Welcome to the **DeepRed-C2** repository, a WebSocket-based Python application designed to simulate real-time Command and Control (C2) communication. This project was developed as a reproducible artifact for our [USENIX WOOT'25](https://www.usenix.org/conference/woot25) paper and aims to provide an interactive environment for studying adversarial C2 behaviors in networked systems.

⚠️ Disclaimer:
This repository is provided strictly for academic and research purposes only. The authors are not responsible for any misuse or unintended consequences.

---

## 📦 Overview

This application emulates a botnet communication system comprising:

- `c2-server.py`: the central C2 server (must be run first).
- `bot.py`: represents an infected bot that connects to the server.
- Runtime configuration is interactively defined (IP, port, adversarial settings, PCAP capture, etc.).

---

## ⚙️ System Requirements

This application has been tested on **Linux (Ubuntu 20.04)**.

### ✅ Install Python 3.11+ and Dependencies

Before running the code, make sure Python 3.11 and related system dependencies are installed:

```bash
sudo apt update
sudo apt install git python3.11-venv python3.11-distutils python3.11-dev python3-pip
```

Then verify pip is compatible:
```bash
python3.11 -m pip --version
# Example output: pip 20.0.2 from /usr/lib/python3/dist-packages/pip (python 3.11)
```
---
## 🚀 Getting Started
1. Clone the Repository
```bash
git clone https://github.com/Mehrdad-hajizadeh/DeepRed-C2.git
cd DeepRed-C2
```
2. Create and Activate Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```
3. Install Python Dependencies

```bash
pip install -r requirements.txt

```
---
## ▶️ Running the Code
Both programs will prompt you for runtime settings like C2 IP, port, adversarial configuration, and optional traffic capture.

### Scapy and Tcpdump Permissions
⚠️ **Attention:**  
For traffic sniffing and PCAP capturing, it is essential to grant the required system-level privileges. Without these, tools used in bot.py (`tcpdump`) or c2-sever.py (`scapy`) may fail to operate properly.

For ```bot.py``` (uses tcpdump before running the code):

```bash
sudo setcap cap_net_raw,cap_net_admin=eip $(which tcpdump)
```
For ```c2-server.py``` (uses scapy):

```bash
sudo setcap cap_net_raw,cap_net_admin=eip $(which scapy)
```


### Start the C2 Server

```bash
cd deepred-c2/src
python c2-server.py
```
### Start the Bot (in a separate terminal or machine)

```bash
cd deepred-c2/src
python bot.py
```
---
## 🗂️ Project Structure


```bash
.
├── dataset       #TUC-RedTeam30: Generated dataset including benign and attack netwrork traffic, collected during 30 different red teaming exercises
├── deepred-c2
│   ├── configs/              # All runtime-generated configs
│   ├── exfiled_data/         # Default folder for received files on the server
│   ├── log/                  # Communication logs for each connected bot
│   ├── pcap/                 # Saved PCAP files (if enabled by the user)
│   ├── sample_file_to_exfil/ # Sample documents for exfiltration
│   │   ├── doc/
│   │   ├── pdf/
│   │   ├── photo/
│   │   └── video/
│   ├── src/
│   │   ├── c2-server.py
│   │   ├── bot.py
│   │   ├── get_bot_ready.py
│   │   ├── ConfigGenerator.py
│   │   ├── network_config_utils.py  

```
---
##  🧰 Troubleshooting

### 🔐 Permission Issues
If you get permission errors related to file writing or access:
```bash
sudo chmod -R 777 configs log pcap exfiled_data
```
---
## 📄 Citation

### DeepRed: A Deep Learning–Powered Command and Control Framework for Multi-Stage Red Teaming Against ML-based Network Intrusion Detection Systems
