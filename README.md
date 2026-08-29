# NetLens Pro — Full-Stack Network Protocol Analyzer & Deep Packet Inspection Suite

NetLens Pro is an end-to-end, modular, and high-performance network analysis and security platform engineered cleanly from scratch in Python with a responsive real-time web dashboard.

---

## 🌟 Key Features

1. **Layered Protocol Decoders (RFC Compliant)**
   - **Layer 2 (Data Link)**: Ethernet II, IEEE 802.1Q VLAN Tagging, ARP.
   - **Layer 3 (Network)**: IPv4 (TOS, DSCP, ECN, fragmentation, checksum verification), IPv6 (Traffic Class, Flow Label, extension headers), ICMPv4/v6.
   - **Layer 4 (Transport)**: TCP (Flags, Sequence/ACK tracking, MSS, Window Scale, Timestamps), UDP.
   - **Layer 7 (Application)**: DNS (Queries, Answers, Label Compression), HTTP/1.x (Headers, Methods, Status), TLS (Record Layer, ClientHello SNI Extraction), DHCP/BOOTP (Options decoding).

2. **Capture & Ingestion Engine**
   - **Cross-Platform Live Raw Sockets**: Native Windows/Linux packet sniffing.
   - **Custom Binary PCAP Engine**: 100% native `.pcap` reader and writer without external native C dependencies.
   - **High-Fidelity Synthetic Traffic Generator**: Realistic multi-protocol simulation for development and testing.

3. **Flow Reassembly & Conversations**
   - 5-Tuple bi-directional flow tracker (`src_ip`, `dst_ip`, `src_port`, `dst_port`, `protocol`).
   - TCP stream sequence reassembly (handles out-of-order segments, duplicates, and payload reconstruction).

4. **Deep Packet Inspection & Security Anomaly Center**
   - Real-time heuristic detection for **Port Scans**, **SYN Floods**, **ARP Spoofing**, **DNS Tunneling / High-Entropy Exfiltration**, and **Cleartext Credentials / Exploit Signatures**.

5. **Query Filter Engine**
   - BPF-like expressive queries (`protocol == tcp`, `ip.src == '192.168.1.10'`, `dst_port == 80`, `payload contains 'GET'`, `threat`).

6. **Responsive Web UI Dashboard**
   - Live packet grid with protocol-specific color badges.
   - Deep layered header inspector & Wireshark-style interactive Hex/ASCII dual-pane viewer.
   - Real-time HTML5 Canvas telemetry charts (Throughput over time, Protocol donut, Top talkers).
   - Conversation matrix with one-click "Follow Stream" dialog.

---

---

## 📦 Dependencies & Installation

NetLens Pro provides complete dependency manifests and deterministic lockfiles across standard package ecosystems (`poetry.lock`, `requirements.lock`, `Pipfile.lock`).

### Manifests & Lockfiles

| Ecosystem / Tool | Manifest | Lockfile |
| :--- | :--- | :--- |
| **Poetry** (Recommended) | `pyproject.toml` | `poetry.lock` |
| **pip / pip-tools** | `requirements.txt` | `requirements.lock` |
| **Pipenv** | `Pipfile` | `Pipfile.lock` |

### 1. Installation

#### Option A: Using Poetry (Recommended)
```bash
# Install dependencies from poetry.lock
poetry install

# Run within poetry environment
poetry run python main.py
```

#### Option B: Using pip with deterministic lockfile
```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install locked dependencies
pip install -r requirements.lock
# Or install using base requirements manifest
pip install -r requirements.txt
```

#### Option C: Using Pipenv
```bash
# Install from Pipfile.lock
pipenv install --deploy
```

---

## 🚀 Quick Start

### 1. Run the Application

```bash
python main.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

### 2. Run Test Suite

```bash
# Run with pytest
python -m pytest

# Or with unittest
python -m unittest discover tests
```

