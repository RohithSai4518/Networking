"""
NetLens Pro - IPv4 Protocol Decoder & Encoder
Decodes IPv4 header fields, checksums, options, and fragmentation.
"""

import socket
import struct
from typing import Tuple, Dict, Any, Optional
from core.models import LayerInfo, ProtocolType


def calculate_ipv4_checksum(header: bytes) -> int:
    if len(header) % 2 != 0:
        header += b"\x00"
    words = struct.unpack(f"!{len(header)//2}H", header)
    checksum = sum(words)
    while checksum >> 16:
        checksum = (checksum & 0xFFFF) + (checksum >> 16)
    return (~checksum) & 0xFFFF


def decode_ipv4(raw_bytes: bytes, offset: int = 0) -> Tuple[Optional[LayerInfo], int, int, int]:
    if len(raw_bytes) - offset < 20:
        return None, 0, 0, offset

    first_byte = raw_bytes[offset]
    version = (first_byte >> 4) & 0x0F
    ihl = (first_byte & 0x0F) * 4

    if version != 4 or ihl < 20 or len(raw_bytes) - offset < ihl:
        return None, 0, 0, offset

    tos, total_len, identification, flags_frag, ttl, protocol, hdr_checksum = struct.unpack(
        "!BHHHBBH", raw_bytes[offset+1:offset+12]
    )

    src_ip = socket.inet_ntoa(raw_bytes[offset+12:offset+16])
    dst_ip = socket.inet_ntoa(raw_bytes[offset+16:offset+20])

    df = bool(flags_frag & 0x4000)
    mf = bool(flags_frag & 0x2000)
    fragment_offset = (flags_frag & 0x1FFF) * 8

    calc_cksum = calculate_ipv4_checksum(raw_bytes[offset:offset+ihl])
    cksum_valid = (calc_cksum == 0)

    fields = {
        "Version": version,
        "Header Length": f"{ihl} bytes",
        "Type of Service": f"0x{tos:02X}",
        "Total Length": total_len,
        "Identification": f"0x{identification:04X} ({identification})",
        "Flags": {
            "Dont Fragment": df,
            "More Fragments": mf,
        },
        "Fragment Offset": fragment_offset,
        "Time to Live": ttl,
        "Protocol": protocol,
        "Header Checksum": f"0x{hdr_checksum:04X} ({'Valid' if cksum_valid else 'Invalid'})",
        "Source IP": src_ip,
        "Destination IP": dst_ip,
    }

    layer = LayerInfo(
        layer_name="IPv4",
        protocol=ProtocolType.IPV4,
        offset=offset,
        length=ihl,
        fields=fields,
        raw_header_hex=raw_bytes[offset:offset+ihl].hex(),
    )

    return layer, protocol, total_len, offset + ihl


def is_private_ip(ip: str) -> bool:
    """Check if IPv4 address is in private range (RFC 1918)."""
    octets = ip.split('.')
    if len(octets) != 4:
        return False
    try:
        first = int(octets[0])
        second = int(octets[1])
        # 10.0.0.0/8
        if first == 10:
            return True
        # 172.16.0.0/12
        if first == 172 and 16 <= second <= 31:
            return True
        # 192.168.0.0/16
        if first == 192 and second == 168:
            return True
        return False
    except ValueError:
        return False


def is_multicast_ip(ip: str) -> bool:
    """Check if IPv4 address is multicast (224.0.0.0/4)."""
    octets = ip.split('.')
    if len(octets) != 4:
        return False
    try:
        first = int(octets[0])
        return 224 <= first <= 239
    except ValueError:
        return False


def is_loopback_ip(ip: str) -> bool:
    """Check if IPv4 address is loopback (127.0.0.0/8)."""
    octets = ip.split('.')
    if len(octets) != 4:
        return False
    try:
        first = int(octets[0])
        return first == 127
    except ValueError:
        return False


def parse_ipv4_options(raw_bytes: bytes, offset: int, ihl: int) -> Dict[str, Any]:
    """Parse IPv4 options if present."""
    options = {}
    if ihl <= 20:
        return options
    
    opts_len = ihl - 20
    opts_data = raw_bytes[offset+20:offset+ihl]
    curr = 0
    
    while curr < opts_len:
        if curr >= len(opts_data):
            break
        opt_type = opts_data[curr]
        if opt_type == 0:  # End of Options List
            break
        if opt_type == 1:  # No Operation
            curr += 1
            continue
        
        if curr + 1 >= len(opts_data):
            break
        opt_len = opts_data[curr+1]
        
        if opt_len == 0:
            break
        
        if curr + opt_len > len(opts_data):
            break
        
        opt_data = opts_data[curr+2:curr+opt_len]
        
        option_names = {
            7: "Record Route",
            68: "Time Stamp",
            137: "MTU Probe",
            130: "Security",
            131: "Loose Source Route",
            137: "Strict Source Route",
        }
        
        options[option_names.get(opt_type, f"Option {opt_type}")] = opt_data.hex()
        curr += opt_len
    
    return options


def build_ipv4_header(src_ip: str, dst_ip: str, protocol: int, payload_len: int, ttl: int = 64) -> bytes:
    """Build an IPv4 header with given parameters."""
    ihl_version = 0x45
    tos = 0
    total_len = 20 + payload_len
    ident = 0x1234
    flags_fragment = 0x4000  # DF
    checksum = 0

    hdr = struct.pack(
        "!BBHHHBBH4s4s",
        ihl_version, tos, total_len, ident, flags_fragment, ttl, protocol, checksum,
        socket.inet_aton(src_ip), socket.inet_aton(dst_ip)
    )
    checksum = calculate_ipv4_checksum(hdr)
    return struct.pack(
        "!BBHHHBBH4s4s",
        ihl_version, tos, total_len, ident, flags_fragment, ttl, protocol, checksum,
        socket.inet_aton(src_ip), socket.inet_aton(dst_ip)
    )


def extract_dscp(tos: int) -> int:
    """Extract DSCP value from Type of Service field."""
    return (tos >> 2) & 0x3F


def extract_ecn(tos: int) -> int:
    """Extract ECN bits from Type of Service field."""
    return tos & 0x03


def parse_tos_dscp(tos: int) -> Dict[str, Any]:
    """Parse Type of Service field into DSCP and ECN components."""
    dscp = extract_dscp(tos)
    ecn = extract_ecn(tos)
    
    dscp_class = dscp >> 3
    dscp_drop = dscp & 0x07
    
    return {
        "DSCP": dscp,
        "DSCP Class": dscp_class,
        "DSCP Drop Precedence": dscp_drop,
        "ECN": ecn,
        "ECN ECT": (ecn & 0x02) != 0,
        "ECN CE": (ecn & 0x01) != 0,
    }


def validate_ipv4_address(ip: str) -> bool:
    """Validate IPv4 address format."""
    octets = ip.split('.')
    if len(octets) != 4:
        return False
    try:
        for octet in octets:
            num = int(octet)
            if num < 0 or num > 255:
                return False
        return True
    except ValueError:
        return False


def calculate_subnet_mask(cidr: int) -> str:
    """Calculate subnet mask from CIDR notation."""
    if cidr < 0 or cidr > 32:
        return "0.0.0.0"
    
    mask = (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF
    return f"{(mask >> 24) & 0xFF}.{(mask >> 16) & 0xFF}.{(mask >> 8) & 0xFF}.{mask & 0xFF}"


def ip_to_int(ip: str) -> int:
    """Convert IPv4 address to integer."""
    octets = ip.split('.')
    if len(octets) != 4:
        return 0
    try:
        return (int(octets[0]) << 24) | (int(octets[1]) << 16) | (int(octets[2]) << 8) | int(octets[3])
    except ValueError:
        return 0


def int_to_ip(ip_int: int) -> str:
    """Convert integer to IPv4 address."""
    return f"{(ip_int >> 24) & 0xFF}.{(ip_int >> 16) & 0xFF}.{(ip_int >> 8) & 0xFF}.{ip_int & 0xFF}"


def are_in_same_subnet(ip1: str, ip2: str, cidr: int) -> bool:
    """Check if two IP addresses are in the same subnet."""
    mask = (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF
    return (ip_to_int(ip1) & mask) == (ip_to_int(ip2) & mask)


def get_broadcast_address(ip: str, cidr: int) -> str:
    """Calculate broadcast address for a network."""
    mask = (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF
    network = ip_to_int(ip) & mask
    broadcast = network | (~mask & 0xFFFFFFFF)
    return int_to_ip(broadcast)


def get_network_address(ip: str, cidr: int) -> str:
    """Calculate network address for a subnet."""
    mask = (0xFFFFFFFF << (32 - cidr)) & 0xFFFFFFFF
    network = ip_to_int(ip) & mask
    return int_to_ip(network)


def parse_fragment_info(flags_frag: int) -> Dict[str, Any]:
    """Parse IPv4 fragmentation flags and offset."""
    df = bool(flags_frag & 0x4000)
    mf = bool(flags_frag & 0x2000)
    fragment_offset = (flags_frag & 0x1FFF) * 8
    
    return {
        "Dont Fragment": df,
        "More Fragments": mf,
        "Fragment Offset": fragment_offset,
        "Is Fragmented": fragment_offset > 0 or mf,
        "Is First Fragment": fragment_offset == 0 and mf,
        "Is Last Fragment": not mf and fragment_offset > 0,
    }


def calculate_ipv4_pseudo_header_checksum(src_ip: str, dst_ip: str, protocol: int, tcp_len: int) -> int:
    """Calculate checksum for IPv4 pseudo header (used in TCP/UDP checksums)."""
    pseudo_header = struct.pack(
        "!4s4sBBH",
        socket.inet_aton(src_ip),
        socket.inet_aton(dst_ip),
        0,
        protocol,
        tcp_len
    )
    return calculate_ipv4_checksum(pseudo_header)


def get_ip_protocol_name(protocol_num: int) -> str:
    """Get protocol name from IP protocol number."""
    protocols = {
        1: "ICMP",
        2: "IGMP",
        6: "TCP",
        17: "UDP",
        41: "IPv6",
        50: "ESP",
        51: "AH",
        58: "ICMPv6",
        89: "OSPF",
        132: "SCTP",
    }
    return protocols.get(protocol_num, f"Protocol {protocol_num}")


def is_fragmented_packet(flags_frag: int) -> bool:
    """Check if packet is fragmented."""
    mf = bool(flags_frag & 0x2000)
    fragment_offset = (flags_frag & 0x1FFF) * 8
    return fragment_offset > 0 or mf


def get_ttl_hop_limit_exceeded(ttl: int) -> bool:
    """Check if TTL has potentially been exceeded (TTL = 1 or 0)."""
    return ttl <= 1


def analyze_ttl(ttl: int) -> Dict[str, Any]:
    """Analyze TTL value to infer potential OS or hop count."""
    # Common initial TTL values by OS
    ttl_ranges = {
        "Windows": [32, 64, 128],
        "Linux/Unix": [64, 255],
        "Cisco": [255],
        "BSD": [64, 255],
    }
    
    possible_os = []
    for os_name, ttls in ttl_ranges.items():
        if ttl in ttls:
            possible_os.append(os_name)
    
    return {
        "TTL": ttl,
        "Possible Initial TTL": [t for t in [32, 64, 128, 255] if t >= ttl],
        "Possible OS": possible_os,
        "Hops Traversed": max([32, 64, 128, 255]) - ttl if ttl <= 128 else 255 - ttl,
    }
