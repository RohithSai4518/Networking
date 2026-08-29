"""
NetLens Pro - Security Anomaly Detector
Detects port scans, high entropy payloads, and malicious signatures.
"""

import math
import re
from typing import List, Dict, Set, Optional, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from core.models import ParsedPacket, SecurityAnomaly, ThreatSeverity, ProtocolType


def calculate_entropy(text: str) -> float:
    if not text:
        return 0.0
    frequencies = {}
    for char in text:
        frequencies[char] = frequencies.get(char, 0) + 1
    entropy = 0.0
    length = len(text)
    for count in frequencies.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


class AnomalyDetector:
    """Security Anomaly Detection Engine."""

    def __init__(self):
        self.scanned_ports: Dict[str, Set[int]] = {}
        self.anomaly_counter = 0
        self.connection_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self dns_queries: Dict[str, List[str]] = defaultdict(list)
        self.high_entropy_threshold = 7.0
        self.syn_flood_threshold = 100
        self.dns_tunneling_threshold = 10
        self.arp_spoofing_cache: Dict[str, Tuple[str, datetime]] = {}

    def analyze_packet(self, packet: ParsedPacket) -> List[SecurityAnomaly]:
        anomalies = []
        meta = packet.metadata
        src_ip = meta.src_ip or "0.0.0.0"
        dst_ip = meta.dst_ip or "0.0.0.0"
        current_time = datetime.now()

        # Port scan detection
        if meta.dst_port and meta.tcp_flags and "SYN" in meta.tcp_flags:
            if src_ip not in self.scanned_ports:
                self.scanned_ports[src_ip] = set()
            self.scanned_ports[src_ip].add(meta.dst_port)

            if len(self.scanned_ports[src_ip]) >= 5:
                self.anomaly_counter += 1
                anomalies.append(SecurityAnomaly(
                    id=f"ANOM-{self.anomaly_counter}",
                    timestamp=meta.timestamp,
                    title="Port Scan Activity Detected",
                    severity=ThreatSeverity.HIGH,
                    source_ip=src_ip,
                    target_ip=dst_ip,
                    description=f"Host {src_ip} probed {len(self.scanned_ports[src_ip])} unique ports.",
                    remediation_tip="Block IP on firewall.",
                ))

        # SYN flood detection
        if meta.tcp_flags and "SYN" in meta.tcp_flags and "ACK" not in meta.tcp_flags:
            self.connection_attempts[src_ip].append(current_time)
            # Clean old attempts (older than 1 minute)
            self.connection_attempts[src_ip] = [
                t for t in self.connection_attempts[src_ip] 
                if current_time - t < timedelta(minutes=1)
            ]
            
            if len(self.connection_attempts[src_ip]) > self.syn_flood_threshold:
                self.anomaly_counter += 1
                anomalies.append(SecurityAnomaly(
                    id=f"ANOM-{self.anomaly_counter}",
                    timestamp=meta.timestamp,
                    title="SYN Flood Attack Detected",
                    severity=ThreatSeverity.CRITICAL,
                    source_ip=src_ip,
                    target_ip=dst_ip,
                    description=f"Host {src_ip} sent {len(self.connection_attempts[src_ip])} SYN packets in 1 minute.",
                    remediation_tip="Enable SYN cookies and rate limiting.",
                ))

        # High entropy payload detection (potential encryption/exfiltration)
        if packet.payload and len(packet.payload) > 50:
            try:
                payload_str = packet.payload.decode('utf-8', errors='ignore')
                entropy = calculate_entropy(payload_str)
                if entropy > self.high_entropy_threshold:
                    self.anomaly_counter += 1
                    anomalies.append(SecurityAnomaly(
                        id=f"ANOM-{self.anomaly_counter}",
                        timestamp=meta.timestamp,
                        title="High Entropy Payload Detected",
                        severity=ThreatSeverity.MEDIUM,
                        source_ip=src_ip,
                        target_ip=dst_ip,
                        description=f"Payload entropy {entropy:.2f} exceeds threshold {self.high_entropy_threshold}. Possible encryption or data exfiltration.",
                        remediation_tip="Inspect payload content and investigate destination.",
                    ))
            except:
                pass

        # DNS tunneling detection
        if meta.protocol == "DNS" and packet.payload:
            try:
                dns_query = self._extract_dns_query(packet.payload)
                if dns_query:
                    self.dns_queries[src_ip].append(dns_query)
                    # Check for unusual subdomain length
                    if len(dns_query) > 50:
                        self.anomaly_counter += 1
                        anomalies.append(SecurityAnomaly(
                            id=f"ANOM-{self.anomaly_counter}",
                            timestamp=meta.timestamp,
                            title="Suspicious DNS Query Length",
                            severity=ThreatSeverity.MEDIUM,
                            source_ip=src_ip,
                            target_ip=dst_ip,
                            description=f"DNS query length {len(dns_query)} exceeds normal range. Possible DNS tunneling.",
                            remediation_tip="Investigate DNS traffic patterns.",
                        ))
            except:
                pass

        # ARP spoofing detection
        if meta.protocol == "ARP" and hasattr(packet, 'layers'):
            arp_layer = next((layer for layer in packet.layers if layer.layer_name == "ARP"), None)
            if arp_layer:
                src_mac = arp_layer.fields.get("Sender MAC")
                target_ip = arp_layer.fields.get("Target IP")
                if src_mac and target_ip:
                    cache_key = f"{target_ip}"
                    if cache_key in self.arp_spoofing_cache:
                        cached_mac, cached_time = self.arp_spoofing_cache[cache_key]
                        if cached_mac != src_mac and (current_time - cached_time) < timedelta(minutes=5):
                            self.anomaly_counter += 1
                            anomalies.append(SecurityAnomaly(
                                id=f"ANOM-{self.anomaly_counter}",
                                timestamp=meta.timestamp,
                                title="ARP Spoofing Detected",
                                severity=ThreatSeverity.HIGH,
                                source_ip=src_ip,
                                target_ip=target_ip,
                                description=f"IP {target_ip} changed MAC from {cached_mac} to {src_mac} within 5 minutes.",
                                remediation_tip="Enable dynamic ARP inspection and investigate network.",
                            ))
                    self.arp_spoofing_cache[cache_key] = (src_mac, current_time)

        return anomalies

    def _extract_dns_query(self, payload: bytes) -> Optional[str]:
        """Extract DNS query from payload."""
        try:
            # Simple DNS query extraction
            if len(payload) > 12:
                # Skip DNS header (12 bytes)
                query_start = 12
                query_parts = []
                pos = query_start
                while pos < len(payload):
                    length = payload[pos]
                    if length == 0:
                        break
                    pos += 1
                    if pos + length > len(payload):
                        break
                    query_part = payload[pos:pos+length].decode('utf-8', errors='ignore')
                    query_parts.append(query_part)
                    pos += length
                return '.'.join(query_parts)
        except:
            pass
        return None


def detect_sql_injection(payload: str) -> bool:
    """Detect potential SQL injection patterns."""
    sql_patterns = [
        r"' OR '1'='1",
        r"' OR 1=1",
        r"UNION SELECT",
        r"DROP TABLE",
        r"INSERT INTO",
        r"UPDATE.*SET",
        r"EXEC\(",
        r"eval\(",
        r"system\(",
        r"shell_exec",
    ]
    for pattern in sql_patterns:
        if re.search(pattern, payload, re.IGNORECASE):
            return True
    return False


def detect_xss(payload: str) -> bool:
    """Detect potential XSS patterns."""
    xss_patterns = [
        r"<script",
        r"javascript:",
        r"onerror=",
        r"onload=",
        r"onclick=",
        r"alert\(",
        r"document\.cookie",
        r"<iframe",
    ]
    for pattern in xss_patterns:
        if re.search(pattern, payload, re.IGNORECASE):
            return True
    return False


def detect_command_injection(payload: str) -> bool:
    """Detect potential command injection patterns."""
    cmd_patterns = [
        r";\s*rm",
        r";\s*ls",
        r";\s*cat",
        r";\s*wget",
        r";\s*curl",
        r"`.*`",
        r"\$\(.*\)",
        r"\|.*rm",
        r"&&.*rm",
    ]
    for pattern in cmd_patterns:
        if re.search(pattern, payload, re.IGNORECASE):
            return True
    return False


def analyze_malicious_signature(payload: str) -> Dict[str, bool]:
    """Analyze payload for various malicious signatures."""
    return {
        "SQL Injection": detect_sql_injection(payload),
        "XSS": detect_xss(payload),
        "Command Injection": detect_command_injection(payload),
        "High Entropy": calculate_entropy(payload) > 7.0,
    }


def detect_suspicious_user_agent(user_agent: str) -> bool:
    """Detect suspicious user agent strings."""
    suspicious_patterns = [
        r"sqlmap",
        r"nikto",
        r"nmap",
        r"metasploit",
        r"burp",
        r"owasp",
        r"zap",
        r"scanner",
        r"crawler",
        r"bot",
    ]
    for pattern in suspicious_patterns:
        if re.search(pattern, user_agent, re.IGNORECASE):
            return True
    return False


def detect_data_exfiltration(payload: str, max_entropy: float = 7.5) -> bool:
    """Detect potential data exfiltration based on payload characteristics."""
    if len(payload) < 100:
        return False
    
    entropy = calculate_entropy(payload)
    if entropy > max_entropy:
        return True
    
    # Check for base64-like patterns
    if re.match(r'^[A-Za-z0-9+/]+={0,2}$', payload):
        return True
    
    return False


def detect_brute_force(attempts: List[datetime], window_minutes: int = 5, threshold: int = 10) -> bool:
    """Detect brute force attack patterns."""
    if len(attempts) < threshold:
        return False
    
    current_time = datetime.now()
    recent_attempts = [
        attempt for attempt in attempts 
        if current_time - attempt < timedelta(minutes=window_minutes)
    ]
    
    return len(recent_attempts) >= threshold


def analyze_protocol_anomalies(protocol: str, packet_size: int) -> Dict[str, Any]:
    """Analyze protocol-specific anomalies."""
    anomalies = []
    
    if protocol == "HTTP":
        if packet_size > 10000:  # Unusually large HTTP request
            anomalies.append("Large HTTP payload - possible data exfiltration")
        if packet_size < 50:  # Suspiciously small HTTP request
            anomalies.append("Small HTTP payload - possible probe")
    
    elif protocol == "DNS":
        if packet_size > 512:  # Unusually large DNS query
            anomalies.append("Large DNS query - possible DNS tunneling")
    
    elif protocol == "ICMP":
        if packet_size > 1500:  # Unusually large ICMP packet
            anomalies.append("Large ICMP packet - possible data exfiltration")
    
    return {
        "protocol": protocol,
        "packet_size": packet_size,
        "anomalies": anomalies,
        "has_anomalies": len(anomalies) > 0,
    }


def detect_suspicious_file_patterns(filename: str) -> bool:
    """Detect suspicious file patterns in URLs or file transfers."""
    suspicious_extensions = [
        '.exe', '.bat', '.cmd', '.scr', '.pif', '.com',
        '.vbs', '.js', '.jar', '.app', '.deb', '.rpm',
        '.sh', '.ps1', '.vb', '.wsf', '.msi'
    ]
    
    suspicious_patterns = [
        r'\.php\?',  # PHP files with query strings
        r'\.jsp\?',  # JSP files with query strings
        r'\.asp\?',  # ASP files with query strings
        r'admin',    # Admin paths
        r'config',   # Config files
        r'backup',   # Backup files
    ]
    
    filename_lower = filename.lower()
    
    for ext in suspicious_extensions:
        if filename_lower.endswith(ext):
            return True
    
    for pattern in suspicious_patterns:
        if re.search(pattern, filename_lower, re.IGNORECASE):
            return True
    
    return False


def calculate_threat_score(anomalies: List[SecurityAnomaly]) -> int:
    """Calculate overall threat score from detected anomalies."""
    if not anomalies:
        return 0
    
    score = 0
    for anomaly in anomalies:
        if anomaly.severity == ThreatSeverity.CRITICAL:
            score += 10
        elif anomaly.severity == ThreatSeverity.HIGH:
            score += 7
        elif anomaly.severity == ThreatSeverity.MEDIUM:
            score += 4
        elif anomaly.severity == ThreatSeverity.LOW:
            score += 1
    
    return min(score, 100)  # Cap at 100


def detect_zero_day_exploit(payload: str, known_signatures: Set[str]) -> bool:
    """Detect potential zero-day exploits by checking against known signatures."""
    # This is a simplified version - in production, you'd use more sophisticated methods
    payload_hash = hash(payload)
    return payload_hash not in known_signatures and len(payload) > 100


def analyze_network_behavior(packets: List[ParsedPacket]) -> Dict[str, Any]:
    """Analyze overall network behavior patterns."""
    if not packets:
        return {"status": "no_data"}
    
    ip_counts = defaultdict(int)
    protocol_counts = defaultdict(int)
    port_counts = defaultdict(int)
    
    for packet in packets:
        if packet.metadata.src_ip:
            ip_counts[packet.metadata.src_ip] += 1
        if packet.metadata.protocol:
            protocol_counts[packet.metadata.protocol] += 1
        if packet.metadata.dst_port:
            port_counts[packet.metadata.dst_port] += 1
    
    top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_protocols = sorted(protocol_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_ports = sorted(port_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "total_packets": len(packets),
        "unique_source_ips": len(ip_counts),
        "top_source_ips": top_ips,
        "protocol_distribution": dict(top_protocols),
        "top_destination_ports": top_ports,
        "analysis_complete": True,
    }
