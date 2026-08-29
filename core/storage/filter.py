"""
NetLens Pro - BPF-like Expression Filter Engine
Evaluates packet fields against expressions like `ip.src == '192.168.1.100' and dst_port == 80`.
"""

from typing import Any, List, Dict, Set, Optional
from core.models import ParsedPacket
import re


class FilterEngine:
    """Evaluates filter query expressions on ParsedPacket instances."""

    def __init__(self):
        self.compiled_filters: Dict[str, Any] = {}
        self.filter_stats: Dict[str, int] = {"total_evaluations": 0, "matches": 0}

    def evaluate(self, packet: ParsedPacket, expression: str) -> bool:
        if not expression or not expression.strip():
            return True

        self.filter_stats["total_evaluations"] += 1
        
        expr = expression.strip().lower()
        meta = packet.metadata
        payload_text = (packet.payload_text or "").lower()

        # Protocol filters
        if expr in ("http", "dns", "tcp", "udp", "arp", "icmp", "tls", "dhcp", "ipv4", "ipv6"):
            result = meta.highest_protocol.lower() == expr or any(l.protocol.value.lower() == expr for l in packet.layers)
            if result:
                self.filter_stats["matches"] += 1
            return result

        # Payload content filters (single)
        if "payload contains" in expr and " and " not in expr and " or " not in expr:
            target = expr.split("payload contains", 1)[1].strip().strip("'").strip('"')
            result = target in payload_text
            if result:
                self.filter_stats["matches"] += 1
            return result

        # Complex expressions with AND/OR
        try:
            # Handle AND expressions
            if " and " in expr.lower():
                parts = expr.split(" and ")
                results = []
                for part in parts:
                    part = part.strip()
                    # Evaluate each part
                    if "payload contains" in part:
                        target = part.split("payload contains", 1)[1].strip().strip("'").strip('"')
                        result = target in payload_text
                    elif "ip.src" in part or "src_ip" in part:
                        result = self._evaluate_ip_filter(part, meta.src_ip)
                    elif "ip.dst" in part or "dst_ip" in part:
                        result = self._evaluate_ip_filter(part, meta.dst_ip)
                    elif "dst_port" in part or "port" in part:
                        result = self._evaluate_port_filter(part, meta.dst_port)
                    elif "src_port" in part:
                        result = self._evaluate_port_filter(part, meta.src_port)
                    elif part in ("http", "dns", "tcp", "udp", "arp", "icmp", "tls", "dhcp", "ipv4", "ipv6"):
                        result = meta.highest_protocol.lower() == part or any(l.protocol.value.lower() == part for l in packet.layers)
                    else:
                        result = True
                    results.append(result)
                final_result = all(results)
                if final_result:
                    self.filter_stats["matches"] += 1
                return final_result
            
            # Handle OR expressions
            if " or " in expr.lower():
                parts = expr.split(" or ")
                results = []
                for part in parts:
                    part = part.strip()
                    if "payload contains" in part:
                        target = part.split("payload contains", 1)[1].strip().strip("'").strip('"')
                        result = target in payload_text
                    elif "ip.src" in part or "src_ip" in part:
                        result = self._evaluate_ip_filter(part, meta.src_ip)
                    elif "ip.dst" in part or "dst_ip" in part:
                        result = self._evaluate_ip_filter(part, meta.dst_ip)
                    elif "dst_port" in part or "port" in part:
                        result = self._evaluate_port_filter(part, meta.dst_port)
                    elif "src_port" in part:
                        result = self._evaluate_port_filter(part, meta.src_port)
                    elif part in ("http", "dns", "tcp", "udp", "arp", "icmp", "tls", "dhcp", "ipv4", "ipv6"):
                        result = meta.highest_protocol.lower() == part or any(l.protocol.value.lower() == part for l in packet.layers)
                    else:
                        result = True
                    results.append(result)
                final_result = any(results)
                if final_result:
                    self.filter_stats["matches"] += 1
                return final_result
            
            # Check individual conditions
            if "ip.src" in expr or "src_ip" in expr:
                result = self._evaluate_ip_filter(expr, meta.src_ip)
                if result:
                    self.filter_stats["matches"] += 1
                return result
            if "ip.dst" in expr or "dst_ip" in expr:
                result = self._evaluate_ip_filter(expr, meta.dst_ip)
                if result:
                    self.filter_stats["matches"] += 1
                return result
            if "dst_port" in expr or "port" in expr:
                result = self._evaluate_port_filter(expr, meta.dst_port)
                if result:
                    self.filter_stats["matches"] += 1
                return result
            if "src_port" in expr:
                result = self._evaluate_port_filter(expr, meta.src_port)
                if result:
                    self.filter_stats["matches"] += 1
                return result
            
            return False
        except:
            return False

    def _evaluate_ip_filter(self, expr: str, ip_value: Optional[str]) -> bool:
        """Evaluate IP address filter expressions."""
        if not ip_value:
            return False
        
        ip_value = ip_value.lower()
        
        if "==" in expr:
            parts = expr.split("==")
            if len(parts) == 2:
                target = parts[1].strip().strip("'").strip('"').lower()
                return ip_value == target.lower()
        
        if "!=" in expr:
            parts = expr.split("!=")
            if len(parts) == 2:
                target = parts[1].strip().strip("'").strip('"').lower()
                return ip_value != target.lower()
        
        if "in" in expr:
            # Handle CIDR notation or IP ranges
            parts = expr.split("in")
            if len(parts) == 2:
                target = parts[1].strip().strip("'").strip('"').lower()
                return self._ip_in_range(ip_value, target)
        
        return False

    def _evaluate_port_filter(self, expr: str, port_value: Optional[int]) -> bool:
        """Evaluate port number filter expressions."""
        if port_value is None:
            return False
        
        if "==" in expr:
            parts = expr.split("==")
            if len(parts) == 2:
                target = parts[1].strip().strip("'").strip('"')
                try:
                    return str(port_value) == target or port_value == int(target)
                except ValueError:
                    return False
        
        if "!=" in expr:
            parts = expr.split("!=")
            if len(parts) == 2:
                target = parts[1].strip().strip("'").strip('"')
                try:
                    return str(port_value) != target and port_value != int(target)
                except ValueError:
                    return True
        
        if ">" in expr:
            parts = expr.split(">")
            if len(parts) == 2:
                target = parts[1].strip()
                try:
                    return port_value > int(target)
                except ValueError:
                    return False
        
        if "<" in expr:
            parts = expr.split("<")
            if len(parts) == 2:
                target = parts[1].strip()
                try:
                    return port_value < int(target)
                except ValueError:
                    return False
        
        return False

    def _evaluate_complex_expression(self, expr: str, packet: ParsedPacket) -> bool:
        """Evaluate complex expressions with AND/OR operators."""
        meta = packet.metadata
        
        def eval_token(tok: str) -> bool:
            if "==" in tok:
                k, v = tok.split("==", 1)
                k, v = k.strip(), v.strip().strip("'").strip('"')
                if k in ("ip.src", "src_ip"):
                    return (meta.src_ip or "").lower() == v.lower()
                if k in ("ip.dst", "dst_ip"):
                    return (meta.dst_ip or "").lower() == v.lower()
                if k in ("dst_port", "port"):
                    return str(meta.dst_port) == v
                if k in ("src_port"):
                    return str(meta.src_port) == v
            return False

        expr_upper = expr.upper()
        if " AND " in expr_upper or " and " in expr:
            parts = expr.replace(" and ", " AND ").split(" AND ")
            results = [eval_token(p.strip()) for p in parts]
            return all(results)
        if " OR " in expr_upper or " or " in expr:
            parts = expr.replace(" or ", " OR ").split(" OR ")
            return any(eval_token(p.strip()) for p in parts)

        return eval_token(expr)

    def _ip_in_range(self, ip: str, range_expr: str) -> bool:
        """Check if IP is in specified range (CIDR or simple range)."""
        # Simple implementation for basic ranges
        if "/" in range_expr:
            # CIDR notation
            ip_parts = ip.split('.')
            range_parts = range_expr.split('/')
            if len(range_parts) == 2:
                network = range_parts[0]
                cidr = int(range_parts[1])
                network_parts = network.split('.')
                if len(ip_parts) == 4 and len(network_parts) == 4:
                    # Simple /24, /16, /8 matching
                    if cidr >= 24:
                        return ip_parts[:3] == network_parts[:3]
                    elif cidr >= 16:
                        return ip_parts[:2] == network_parts[:2]
                    elif cidr >= 8:
                        return ip_parts[0] == network_parts[0]
        return False

    def compile_filter(self, expression: str) -> str:
        """Compile a filter expression for faster evaluation."""
        # In a production system, this would compile to bytecode or AST
        filter_id = f"filter_{len(self.compiled_filters)}"
        self.compiled_filters[filter_id] = expression
        return filter_id

    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filter evaluation statistics."""
        match_rate = 0.0
        if self.filter_stats["total_evaluations"] > 0:
            match_rate = self.filter_stats["matches"] / self.filter_stats["total_evaluations"]
        
        return {
            **self.filter_stats,
            "match_rate": match_rate,
            "compiled_filters": len(self.compiled_filters)
        }

    def reset_stats(self):
        """Reset filter statistics."""
        self.filter_stats = {"total_evaluations": 0, "matches": 0}


class AdvancedFilterEngine(FilterEngine):
    """Advanced filter engine with additional capabilities."""

    def __init__(self):
        super().__init__()
        self.mac_address_cache: Dict[str, Set[str]] = {}
        self.dns_cache: Dict[str, List[str]] = {}

    def evaluate(self, packet: ParsedPacket, expression: str) -> bool:
        """Enhanced evaluation with MAC address and DNS filtering."""
        # First try basic evaluation
        if super().evaluate(packet, expression):
            return True
        
        # MAC address filtering
        if "mac.src" in expression or "mac.dst" in expression:
            return self._evaluate_mac_filter(packet, expression)
        
        # DNS filtering
        if "dns" in expression.lower():
            return self._evaluate_dns_filter(packet, expression)
        
        # Time-based filtering
        if "time" in expression.lower():
            return self._evaluate_time_filter(packet, expression)
        
        return False

    def _evaluate_mac_filter(self, packet: ParsedPacket, expression: str) -> bool:
        """Evaluate MAC address filter expressions."""
        meta = packet.metadata
        
        if "mac.src" in expression:
            if "==" in expression:
                parts = expression.split("==")
                if len(parts) == 2:
                    target = parts[1].strip().strip("'").strip('"').lower()
                    return (meta.src_mac or "").lower() == target
        
        if "mac.dst" in expression:
            if "==" in expression:
                parts = expression.split("==")
                if len(parts) == 2:
                    target = parts[1].strip().strip("'").strip('"').lower()
                    return (meta.dst_mac or "").lower() == target
        
        return False

    def _evaluate_dns_filter(self, packet: ParsedPacket, expression: str) -> bool:
        """Evaluate DNS-related filter expressions."""
        if packet.metadata.protocol != "DNS":
            return False
        
        # Check for DNS query names in payload
        if "query" in expression.lower():
            target = expression.split("query")[1].strip().strip("'").strip('"').lower()
            payload_text = (packet.payload_text or "").lower()
            return target in payload_text
        
        return False

    def _evaluate_time_filter(self, packet: ParsedPacket, expression: str) -> bool:
        """Evaluate time-based filter expressions."""
        from datetime import datetime
        
        if "after" in expression.lower():
            # Simple time comparison (would need proper parsing in production)
            return True  # Placeholder
        
        if "before" in expression.lower():
            return True  # Placeholder
        
        return False

    def add_mac_mapping(self, ip: str, mac: str):
        """Add IP to MAC address mapping."""
        if ip not in self.mac_address_cache:
            self.mac_address_cache[ip] = set()
        self.mac_address_cache[ip].add(mac.lower())

    def get_mac_for_ip(self, ip: str) -> Optional[str]:
        """Get MAC address for a given IP."""
        if ip in self.mac_address_cache and self.mac_address_cache[ip]:
            return list(self.mac_address_cache[ip])[0]
        return None


def create_filter_expression(conditions: List[Dict[str, Any]]) -> str:
    """Create a filter expression from a list of conditions."""
    expressions = []
    
    for condition in conditions:
        field = condition.get("field", "")
        operator = condition.get("operator", "==")
        value = condition.get("value", "")
        
        expressions.append(f"{field} {operator} '{value}'")
    
    return " and ".join(expressions)


def parse_filter_expression(expression: str) -> List[Dict[str, Any]]:
    """Parse a filter expression into individual conditions."""
    conditions = []
    
    # Split by AND/OR operators
    parts = re.split(r'\s+(and|or)\s+', expression, flags=re.IGNORECASE)
    
    for i in range(0, len(parts), 2):
        if i < len(parts):
            condition_str = parts[i].strip()
            
            # Parse individual condition
            if "==" in condition_str:
                field, value = condition_str.split("==", 1)
                conditions.append({
                    "field": field.strip(),
                    "operator": "==",
                    "value": value.strip().strip("'").strip('"')
                })
            elif "!=" in condition_str:
                field, value = condition_str.split("!=", 1)
                conditions.append({
                    "field": field.strip(),
                    "operator": "!=",
                    "value": value.strip().strip("'").strip('"')
                })
    
    return conditions


def validate_filter_expression(expression: str) -> bool:
    """Validate a filter expression syntax."""
    try:
        # Basic syntax validation
        if not expression or not expression.strip():
            return True
        
        # Check for balanced quotes
        single_quotes = expression.count("'")
        double_quotes = expression.count('"')
        
        if single_quotes % 2 != 0 or double_quotes % 2 != 0:
            return False
        
        # Check for valid operators
        valid_operators = ["==", "!=", ">", "<", ">=", "<=", "contains", "in"]
        has_valid_operator = any(op in expression for op in valid_operators)
        
        if not has_valid_operator and "and" not in expression.lower() and "or" not in expression.lower():
            # Allow simple protocol names
            valid_protocols = ["http", "dns", "tcp", "udp", "arp", "icmp", "tls", "dhcp", "ipv4", "ipv6"]
            if expression.lower() not in valid_protocols:
                return False
        
        return True
        
    except Exception:
        return False