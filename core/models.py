"""
NetLens Pro - Data Models
Defines core representations for packets, protocol layers, network flows,
security anomalies, and telemetry statistics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
import time


class ProtocolType(str, Enum):
    ETHERNET = "Ethernet"
    ARP = "ARP"
    IPV4 = "IPv4"
    IPV6 = "IPv6"
    ICMP = "ICMP"
    ICMPV6 = "ICMPv6"
    TCP = "TCP"
    UDP = "UDP"
    DNS = "DNS"
    HTTP = "HTTP"
    TLS = "TLS"
    DHCP = "DHCP"
    UNKNOWN = "Unknown"


class ThreatSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class LayerInfo:
    """Represents decoded fields and byte ranges for a specific network layer."""
    layer_name: str
    protocol: ProtocolType
    offset: int
    length: int
    fields: Dict[str, Any] = field(default_factory=dict)
    raw_header_hex: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_name": self.layer_name,
            "protocol": self.protocol.value,
            "offset": self.offset,
            "length": self.length,
            "fields": self.fields,
            "raw_header_hex": self.raw_header_hex,
        }


@dataclass
class PacketMetadata:
    """Core indexed metadata of a network packet."""
    id: int
    timestamp: float
    length: int
    highest_protocol: str
    src_mac: Optional[str] = None
    dst_mac: Optional[str] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    info: str = ""
    tcp_flags: Optional[List[str]] = None
    is_anomaly: bool = False
    anomaly_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "timestamp_formatted": time.strftime("%H:%M:%S", time.localtime(self.timestamp)) + f".{int((self.timestamp % 1) * 1000):03d}",
            "length": self.length,
            "highest_protocol": self.highest_protocol,
            "src_mac": self.src_mac,
            "dst_mac": self.dst_mac,
            "src_ip": self.src_ip or self.src_mac or "N/A",
            "dst_ip": self.dst_ip or self.dst_mac or "N/A",
            "src_port": self.src_port,
            "dst_port": self.dst_port,
            "info": self.info,
            "tcp_flags": self.tcp_flags or [],
            "is_anomaly": self.is_anomaly,
            "anomaly_reason": self.anomaly_reason,
        }


@dataclass
class ParsedPacket:
    """Full representation of a decoded packet including all layers and raw binary payload."""
    metadata: PacketMetadata
    layers: List[LayerInfo] = field(default_factory=list)
    raw_hex: str = ""
    payload_hex: str = ""
    payload_text: str = ""

    def to_dict(self, include_raw: bool = True) -> Dict[str, Any]:
        result = {
            "metadata": self.metadata.to_dict(),
            "layers": [layer.to_dict() for layer in self.layers],
        }
        if include_raw:
            result["raw_hex"] = self.raw_hex
            result["payload_hex"] = self.payload_hex
            result["payload_text"] = self.payload_text
        return result


@dataclass
class FlowKey:
    """5-Tuple network flow identifier."""
    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str

    def canonical(self) -> "FlowKey":
        """Return a canonical bi-directional flow key."""
        if (self.src_ip, self.src_port) <= (self.dst_ip, self.dst_port):
            return FlowKey(self.src_ip, self.dst_ip, self.src_port, self.dst_port, self.protocol)
        return FlowKey(self.dst_ip, self.src_ip, self.dst_port, self.src_port, self.protocol)

    def to_string(self) -> str:
        return f"{self.src_ip}:{self.src_port} <-> {self.dst_ip}:{self.dst_port} ({self.protocol})"


@dataclass
class NetworkFlow:
    """Tracks state and statistics of an active communication stream."""
    key: FlowKey
    start_time: float
    last_seen: float
    total_packets_forward: int = 0
    total_packets_reverse: int = 0
    total_bytes_forward: int = 0
    total_bytes_reverse: int = 0
    state: str = "ESTABLISHED"
    application: str = "Unknown"
    reconstructed_text: str = ""

    @property
    def total_packets(self) -> int:
        return self.total_packets_forward + self.total_packets_reverse

    @property
    def total_bytes(self) -> int:
        return self.total_bytes_forward + self.total_bytes_reverse

    @property
    def duration(self) -> float:
        return max(0.001, self.last_seen - self.start_time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key.to_string(),
            "src": f"{self.key.src_ip}:{self.key.src_port}",
            "dst": f"{self.key.dst_ip}:{self.key.dst_port}",
            "protocol": self.key.protocol,
            "start_time": self.start_time,
            "last_seen": self.last_seen,
            "duration": round(self.duration, 3),
            "packets_forward": self.total_packets_forward,
            "packets_reverse": self.total_packets_reverse,
            "bytes_forward": self.total_bytes_forward,
            "bytes_reverse": self.total_bytes_reverse,
            "total_packets": self.total_packets,
            "total_bytes": self.total_bytes,
            "state": self.state,
            "application": self.application,
        }


@dataclass
class SecurityAnomaly:
    """Details of a detected network threat or behavioral anomaly."""
    id: str
    timestamp: float
    title: str
    severity: ThreatSeverity
    source_ip: str
    target_ip: Optional[str]
    description: str
    evidence_packet_ids: List[int] = field(default_factory=list)
    remediation_tip: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "timestamp_formatted": time.strftime("%H:%M:%S", time.localtime(self.timestamp)),
            "title": self.title,
            "severity": self.severity.value,
            "source_ip": self.source_ip,
            "target_ip": self.target_ip or "N/A",
            "description": self.description,
            "evidence_packet_ids": self.evidence_packet_ids,
            "remediation_tip": self.remediation_tip,
        }


@dataclass
class NetworkStats:
    """Real-time statistical aggregation of captured traffic."""
    total_packets: int = 0
    total_bytes: int = 0
    packets_per_second: float = 0.0
    bytes_per_second: float = 0.0
    protocol_distribution: Dict[str, int] = field(default_factory=dict)
    top_sources: Dict[str, int] = field(default_factory=dict)
    top_destinations: Dict[str, int] = field(default_factory=dict)
    active_flow_count: int = 0
    anomaly_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_packets": self.total_packets,
            "total_bytes": self.total_bytes,
            "packets_per_second": round(self.packets_per_second, 2),
            "bytes_per_second": round(self.bytes_per_second, 2),
            "mbps": round((self.bytes_per_second * 8) / 1_000_000, 4),
            "protocol_distribution": self.protocol_distribution,
            "top_sources": self.top_sources,
            "top_destinations": self.top_destinations,
            "active_flow_count": self.active_flow_count,
            "anomaly_count": self.anomaly_count,
        }
