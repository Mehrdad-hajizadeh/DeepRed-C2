# DeepRed Command and Control (C2)

This repository contains a WebSocket-based Python application designed to simulate real-time DeepRed Command and Control (C2) communication. The project consists of two primary files: `c2-server.py` that initializes the C2 server and should be run first, and `bot.py` that represents an infected machine (bot). Once started, it prompts the user for configuration settings, including: defining the C2 server IP/Port, adversarial perturbation, traffic collection in a PCAP, etc.

This repository was developed as an artifact accompanying our USENIX WOOT'25 paper. It provides an interactive environment for users to explore the behavior of C2-based communication and security research.

---

## 📦 Contents

- `c2-server.py` — WebSocket server that listens for network packet events.
- `bot.py` — WebSocket client as bot which initial a connection to tthat receives and logs data.
- `get_bot_ready.py` — Take custom configuration for bot<->C2 communicaiton.
- `network_config_utils.py` — Get C2 network configuration ready 
- `ConfigGenerator.py` — Generates runtime configurations.
- `TUC-RedTeam30.csv` — Generated dataset 
---

## ⚙️ Requirements

- **OS:** Ubuntu 20.04 or 22.04
- **Python:** 3.11+
- **Privileges:** Root is required (due to `scapy` using raw sockets for traffic monitoring)

---

## Installation

## Folder Structure

## Troubleshooting 

## Additional information
