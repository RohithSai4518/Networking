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

## 🚀 Quick Start

### 1. Installation

Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python main.py
```
Open your browser and navigate to:
```
http://127.0.0.1:8000
```

### 3. Run Test Suite

```bash
python -m unittest discover tests
```
