"""
NetLens Pro - TCP Protocol Decoder & State Machine Tracker
Decodes TCP headers, flags, options (MSS, Window Scale, SACK, Timestamps), sequence numbers.
"""

import struct
from typing import Tuple, Dict, Any, Optional, List
from core.models import LayerInfo, ProtocolType


def decode_tcp(raw_bytes: bytes, offset: int = 0) -> Tuple[Optional[LayerInfo], int, int, List[str], int]:
    if len(raw_bytes) - offset < 20:
        return None, 0, 0, [], offset

    src_port, dst_port, seq_num, ack_num, data_offset_flags, window_size, checksum, urg_ptr = struct.unpack(
        "!HHIIHHHH", raw_bytes[offset:offset+20]
    )

    data_offset = ((data_offset_flags >> 12) & 0x0F) * 4
    flags_val = data_offset_flags & 0x01FF

    if data_offset < 20 or len(raw_bytes) - offset < data_offset:
        return None, 0, 0, [], offset

    flag_names = []
    if flags_val & 0x001: flag_names.append("FIN")
    if flags_val & 0x002: flag_names.append("SYN")
    if flags_val & 0x004: flag_names.append("RST")
    if flags_val & 0x008: flag_names.append("PSH")
    if flags_val & 0x010: flag_names.append("ACK")
    if flags_val & 0x020: flag_names.append("URG")
    if flags_val & 0x040: flag_names.append("ECE")
    if flags_val & 0x080: flag_names.append("CWR")
    if flags_val & 0x100: flag_names.append("NS")

    fields = {
        "Source Port": src_port,
        "Destination Port": dst_port,
        "Sequence Number": seq_num,
        "Acknowledgment Number": ack_num,
        "Header Length": f"{data_offset} bytes",
        "Flags": {
            "FIN": bool(flags_val & 0x001),
            "SYN": bool(flags_val & 0x002),
            "RST": bool(flags_val & 0x004),
            "PSH": bool(flags_val & 0x008),
            "ACK": bool(flags_val & 0x010),
            "URG": bool(flags_val & 0x020),
            "ECE": bool(flags_val & 0x040),
            "CWR": bool(flags_val & 0x080),
        },
        "Flag List": flag_names,
        "Window Size": window_size,
        "Checksum": f"0x{checksum:04X}",
        "Urgent Pointer": urg_ptr,
    }

    layer = LayerInfo(
        layer_name="TCP",
        protocol=ProtocolType.TCP,
        offset=offset,
        length=data_offset,
        fields=fields,
        raw_header_hex=raw_bytes[offset:offset+data_offset].hex(),
    )

    return layer, src_port, dst_port, flag_names, offset + data_offset


def parse_tcp_options(raw_bytes: bytes, offset: int, data_offset: int) -> Dict[str, Any]:
    """Parse TCP options if present."""
    options = {}
    if data_offset <= 20:
        return options
    
    opts_len = data_offset - 20
    opts_data = raw_bytes[offset+20:offset+data_offset]
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
            2: "Maximum Segment Size",
            3: "Window Scale",
            4: "SACK Permitted",
            5: "SACK",
            8: "Timestamps",
            19: "TCP MD5 Signature",
            28: "User Timeout",
            29: "Authentication",
            34: "TCP Fast Open",
        }
        
        if opt_type == 2 and len(opt_data) >= 2:
            mss = struct.unpack("!H", opt_data[:2])[0]
            options["MSS"] = mss
        elif opt_type == 3 and len(opt_data) >= 1:
            window_scale = opt_data[0]
            options["Window Scale"] = window_scale
        elif opt_type == 8 and len(opt_data) >= 8:
            ts_val = struct.unpack("!I", opt_data[:4])[0]
            ts_echo = struct.unpack("!I", opt_data[4:8])[0]
            options["Timestamp Value"] = ts_val
            options["Timestamp Echo"] = ts_echo
        else:
            options[option_names.get(opt_type, f"Option {opt_type}")] = opt_data.hex()
        
        curr += opt_len
    
    return options


def calculate_tcp_checksum(src_ip: str, dst_ip: str, src_port: int, dst_port: int, 
                            seq_num: int, ack_num: int, data_offset_flags: int, 
                            window_size: int, checksum: int, urg_ptr: int, 
                            payload: bytes) -> int:
    """Calculate TCP checksum with pseudo header."""
    from core.protocols.ipv4 import calculate_ipv4_pseudo_header_checksum
    
    tcp_len = 20 + len(payload)
    pseudo_checksum = calculate_ipv4_pseudo_header_checksum(src_ip, dst_ip, 6, tcp_len)
    
    tcp_header = struct.pack(
        "!HHIIHHHH",
        src_port, dst_port, seq_num, ack_num, data_offset_flags, window_size, 0, urg_ptr
    )
    
    # Combine pseudo header, TCP header, and payload
    combined = tcp_header + payload
    if len(combined) % 2 != 0:
        combined += b"\x00"
    
    words = struct.unpack(f"!{len(combined)//2}H", combined)
    calc_checksum = sum(words) + pseudo_checksum
    
    while calc_checksum >> 16:
        calc_checksum = (calc_checksum & 0xFFFF) + (calc_checksum >> 16)
    
    return (~calc_checksum) & 0xFFFF


def analyze_tcp_connection_state(flags: List[str], seq_num: int, ack_num: int) -> Dict[str, Any]:
    """Analyze TCP connection state based on flags and sequence numbers."""
    has_syn = "SYN" in flags
    has_ack = "ACK" in flags
    has_fin = "FIN" in flags
    has_rst = "RST" in flags
    
    state = "UNKNOWN"
    
    if has_rst:
        state = "RESET"
    elif has_syn and not has_ack:
        state = "SYN_SENT"
    elif has_syn and has_ack:
        state = "SYN_RECEIVED"
    elif has_fin and has_ack:
        state = "CLOSING"
    elif has_fin and not has_ack:
        state = "FIN_WAIT_1"
    elif has_ack and not has_syn and not has_fin:
        state = "ESTABLISHED"
    
    return {
        "Connection State": state,
        "Is SYN": has_syn,
        "Is ACK": has_ack,
        "Is FIN": has_fin,
        "Is RST": has_rst,
        "Sequence Number": seq_num,
        "Acknowledgment Number": ack_num if has_ack else None,
    }


def calculate_rtt_estimation(ts_val: int, ts_echo: int) -> Optional[float]:
    """Calculate Round Trip Time from TCP timestamps."""
    if ts_val == 0 or ts_echo == 0:
        return None
    rtt = (ts_val - ts_echo) / 1000.0  # Convert milliseconds to seconds
    return max(0.0, rtt)


def analyze_window_scaling(window_size: int, window_scale: int) -> Dict[str, Any]:
    """Analyze TCP window scaling and effective window size."""
    scale_factor = 2 ** window_scale if window_scale > 0 else 1
    effective_window = window_size * scale_factor
    
    return {
        "Window Size": window_size,
        "Window Scale Factor": window_scale,
        "Scale Multiplier": scale_factor,
        "Effective Window Size": effective_window,
        "Effective Window (KB)": effective_window / 1024,
    }


def is_tcp_retransmission(seq_num: int, prev_seq_num: int, payload_len: int) -> bool:
    """Detect potential TCP retransmission based on sequence numbers."""
    return seq_num == prev_seq_num and payload_len > 0


def calculate_tcp_throughput(bytes_transferred: int, duration: float) -> float:
    """Calculate TCP throughput in Mbps."""
    if duration <= 0:
        return 0.0
    bits_per_second = (bytes_transferred * 8) / duration
    return bits_per_second / 1_000_000  # Convert to Mbps


def detect_tcp_out_of_order(seq_num: int, expected_seq_num: int) -> bool:
    """Detect out-of-order TCP segments."""
    return seq_num > expected_seq_num


def analyze_tcp_flags(flags: List[str]) -> Dict[str, Any]:
    """Analyze TCP flag combinations for connection phases."""
    flag_set = set(flags)
    
    connection_phase = "UNKNOWN"
    if "SYN" in flag_set and "ACK" not in flag_set:
        connection_phase = "CONNECTION_INITIATION"
    elif "SYN" in flag_set and "ACK" in flag_set:
        connection_phase = "CONNECTION_ESTABLISHMENT"
    elif "FIN" in flag_set:
        connection_phase = "CONNECTION_TERMINATION"
    elif "RST" in flag_set:
        connection_phase = "CONNECTION_RESET"
    elif "ACK" in flag_set and len(flag_set) == 1:
        connection_phase = "DATA_TRANSFER"
    
    return {
        "Connection Phase": connection_phase,
        "Flag Count": len(flags),
        "Flags": flags,
        "Is Control Packet": len(flag_set) > 1 or ("ACK" in flag_set and len(flag_set) == 1),
    }


def get_well_known_port_service(port: int) -> str:
    """Get service name for well-known TCP ports."""
    well_known_ports = {
        20: "FTP Data",
        21: "FTP Control",
        22: "SSH",
        23: "Telnet",
        25: "SMTP",
        53: "DNS",
        67: "DHCP Server",
        68: "DHCP Client",
        80: "HTTP",
        110: "POP3",
        143: "IMAP",
        443: "HTTPS",
        445: "SMB",
        465: "SMTPS",
        587: "SMTP Submission",
        993: "IMAPS",
        995: "POP3S",
        1433: "MSSQL",
        1521: "Oracle DB",
        3306: "MySQL",
        3389: "RDP",
        5432: "PostgreSQL",
        5900: "VNC",
        6379: "Redis",
        8080: "HTTP Alternate",
        8443: "HTTPS Alternate",
        27017: "MongoDB",
    }
    return well_known_ports.get(port, f"Port {port}")


def analyze_tcp_header_prediction(src_port: int, dst_port: int, seq_num: int, 
                                  ack_num: int, window_size: int) -> Dict[str, Any]:
    """Analyze TCP header for header prediction optimization."""
    is_simple_ack = ("ACK" in ["ACK"] and src_port > 1024 and dst_port > 1024)
    has_data = False  # Would need payload analysis
    
    return {
        "Can Use Header Prediction": is_simple_ack and not has_data,
        "Source Port Service": get_well_known_port_service(src_port),
        "Destination Port Service": get_well_known_port_service(dst_port),
        "Window Size (bytes)": window_size,
        "Window Size (KB)": window_size / 1024,
    }


def detect_zero_window_probe(window_size: int, seq_num: int, payload_len: int) -> bool:
    """Detect TCP zero window probe."""
    return window_size == 0 and payload_len == 1


def detect_window_update(window_size: int, prev_window_size: int) -> bool:
    """Detect TCP window update."""
    return window_size > prev_window_size and prev_window_size == 0


def calculate_congestion_window(cwnd: int, ssthresh: int) -> Dict[str, Any]:
    """Calculate TCP congestion window state."""
    phase = "UNKNOWN"
    if cwnd < ssthresh:
        phase = "SLOW_START"
    elif cwnd > ssthresh:
        phase = "CONGESTION_AVOIDANCE"
    else:
        phase = "TRANSITION"
    
    return {
        "Congestion Window": cwnd,
        "Slow Start Threshold": ssthresh,
        "Congestion Phase": phase,
    }


def analyze_tcp_segment_size(payload_len: int, mss: Optional[int] = None) -> Dict[str, Any]:
    """Analyze TCP segment size relative to MSS."""
    if mss is None:
        mss = 1460  # Default MSS
    
    is_full_segment = payload_len == mss
    is_partial_segment = 0 < payload_len < mss
    is_empty_segment = payload_len == 0
    
    return {
        "Segment Size": payload_len,
        "MSS": mss,
        "Is Full Segment": is_full_segment,
        "Is Partial Segment": is_partial_segment,
        "Is Empty Segment": is_empty_segment,
        "Utilization": (payload_len / mss) * 100 if mss > 0 else 0,
    }


def detect_tcp_keepalive(seq_num: int, ack_num: int, payload_len: int) -> bool:
    """Detect TCP keepalive packets."""
    return payload_len == 1 or (payload_len == 0 and seq_num == ack_num - 1)


def analyze_tcp_urgency(urg_ptr: int, flags: List[str]) -> Dict[str, Any]:
    """Analyze TCP urgent data."""
    has_urg = "URG" in flags
    
    return {
        "Has Urgent Data": has_urg,
        "Urgent Pointer": urg_ptr if has_urg else None,
        "Urgent Offset": urg_ptr if has_urg else None,
    }


def calculate_sequence_space_distance(seq1: int, seq2: int) -> int:
    """Calculate distance between two sequence numbers handling wraparound."""
    diff = seq2 - seq1
    if diff < 0:
        diff += 2**32  # Handle 32-bit sequence number wraparound
    return diff


def detect_sequence_wraparound(seq_num: int, prev_seq_num: int) -> bool:
    """Detect TCP sequence number wraparound."""
    return seq_num < prev_seq_num and (prev_seq_num - seq_num) > 2**31
