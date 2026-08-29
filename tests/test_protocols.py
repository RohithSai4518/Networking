"""
Unit Tests for Protocol Decoders
Validates RFC-compliant binary decoding across all protocol layers.
"""

import socket
import struct
import unittest
from core.models import ProtocolType
from core.protocols.ethernet import decode_ethernet
from core.protocols.arp import decode_arp
from core.protocols.ipv4 import decode_ipv4, calculate_ipv4_checksum
from core.protocols.ipv6 import decode_ipv6
from core.protocols.icmp import decode_icmp
from core.protocols.tcp import decode_tcp
from core.protocols.udp import decode_udp
from core.protocols.dns import decode_dns
from core.protocols.http import decode_http
from core.protocols.tls import decode_tls
from core.protocols.dhcp import decode_dhcp
from core.protocols.decoder import PacketDecoder
from core.capture.generator import (
    build_ethernet_header,
    build_ipv4_header,
    build_tcp_segment,
    build_udp_datagram,
    build_dns_query,
    build_arp_packet,
)


class TestProtocolDecoders(unittest.TestCase):

    def test_ethernet_decoder(self):
        eth_frame = build_ethernet_header("00:11:22:33:44:55", "66:77:88:99:AA:BB", 0x0800)
        layer, ethertype, offset = decode_ethernet(eth_frame, 0)
        
        self.assertIsNotNone(layer)
        self.assertEqual(ethertype, 0x0800)
        self.assertEqual(layer.fields["Source MAC"], "00:11:22:33:44:55")
        self.assertEqual(layer.fields["Destination MAC"], "66:77:88:99:aa:bb")
        self.assertEqual(offset, 14)

    def test_arp_decoder(self):
        arp_pkt = build_arp_packet(1, "00:11:22:33:44:55", "192.168.1.10", "00:00:00:00:00:00", "192.168.1.1")
        layer, offset = decode_arp(arp_pkt, 0)
        
        self.assertIsNotNone(layer)
        self.assertEqual(layer.fields["Sender IP"], "192.168.1.10")
        self.assertEqual(layer.fields["Target IP"], "192.168.1.1")
        self.assertIn("Who has 192.168.1.1", layer.fields["Summary"])

    def test_ipv4_decoder_and_checksum(self):
        src_ip = "192.168.1.50"
        dst_ip = "8.8.8.8"
        dummy_payload = b"Hello IP"
        ip_pkt = build_ipv4_header(src_ip, dst_ip, 6, len(dummy_payload)) + dummy_payload

        layer, proto, total_len, offset = decode_ipv4(ip_pkt, 0)
        self.assertIsNotNone(layer)
        self.assertEqual(proto, 6)
        self.assertEqual(layer.fields["Source IP"], src_ip)
        self.assertEqual(layer.fields["Destination IP"], dst_ip)
        self.assertIn("Valid", layer.fields["Header Checksum"])

    def test_tcp_decoder(self):
        payload = b"GET / HTTP/1.1\r\n\r\n"
        tcp_seg = build_tcp_segment(54321, 80, 1000, 2000, 0x018, payload)  # PSH+ACK
        
        layer, src_port, dst_port, flags, offset = decode_tcp(tcp_seg, 0)
        self.assertIsNotNone(layer)
        self.assertEqual(src_port, 54321)
        self.assertEqual(dst_port, 80)
        self.assertTrue(layer.fields["Flags"]["ACK"])
        self.assertTrue(layer.fields["Flags"]["PSH"])
        self.assertFalse(layer.fields["Flags"]["SYN"])

    def test_udp_decoder(self):
        payload = b"DNS Test Payload"
        udp_datagram = build_udp_datagram(53535, 53, payload)
        
        layer, src_port, dst_port, length, offset = decode_udp(udp_datagram, 0)
        self.assertIsNotNone(layer)
        self.assertEqual(src_port, 53535)
        self.assertEqual(dst_port, 53)
        self.assertEqual(length, 8 + len(payload))

    def test_dns_decoder(self):
        dns_query = build_dns_query("api.example.com", 1, txn_id=0x9999)
        layer, offset = decode_dns(dns_query, 0)
        
        self.assertIsNotNone(layer)
        self.assertEqual(layer.fields["Transaction ID"], "0x9999")
        self.assertEqual(len(layer.fields["Questions"]), 1)
        self.assertEqual(layer.fields["Questions"][0]["name"], "api.example.com")
        self.assertEqual(layer.fields["Questions"][0]["type"], "A")

    def test_http_decoder(self):
        http_data = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 5\r\n\r\nHello"
        layer, offset = decode_http(http_data, 0)
        
        self.assertIsNotNone(layer)
        self.assertEqual(layer.fields["Type"], "HTTP Response")
        self.assertEqual(layer.fields["Status Code"], 200)
        self.assertEqual(layer.fields["Headers"]["Content-Type"], "text/plain")

    def test_icmp_decoder(self):
        # Type 8 Code 0 Echo Request, ID 0x1234, Seq 0x0001
        icmp_pkt = struct.pack("!BBHHH", 8, 0, 0x5c4b, 0x1234, 1) + b"PingPayload"
        layer, offset = decode_icmp(icmp_pkt, 0)
        self.assertIsNotNone(layer)
        self.assertEqual(layer.fields["Type"], 8)
        self.assertEqual(layer.fields["Type Name"], "Echo Request")
        self.assertEqual(layer.fields["Identifier"], 0x1234)
        self.assertEqual(layer.fields["Sequence Number"], 1)

    def test_ipv6_decoder(self):
        src_ip = "2001:db8::1"
        dst_ip = "2001:db8::2"
        src_bytes = socket.inet_pton(socket.AF_INET6, src_ip)
        dst_bytes = socket.inet_pton(socket.AF_INET6, dst_ip)
        vtc_flow = (6 << 28)
        hdr = struct.pack("!IHBB", vtc_flow, 16, 58, 64) + src_bytes + dst_bytes
        layer, next_hdr, offset = decode_ipv6(hdr, 0)
        self.assertIsNotNone(layer)
        self.assertEqual(layer.fields["Version"], 6)
        self.assertEqual(layer.fields["Source IP"], src_ip)
        self.assertEqual(layer.fields["Destination IP"], dst_ip)
        self.assertEqual(next_hdr, 58)
        self.assertEqual(offset, 40)

    def test_master_packet_decoder(self):
        # Build complete Ethernet + IPv4 + UDP + DNS frame
        dns_bytes = build_dns_query("test.local", 1)
        udp_bytes = build_udp_datagram(50000, 53, dns_bytes)
        ip_bytes = build_ipv4_header("192.168.1.100", "8.8.8.8", 17, len(udp_bytes)) + udp_bytes
        eth_frame = build_ethernet_header("00:11:22:33:44:55", "52:54:00:12:34:01", 0x0800) + ip_bytes

        decoder = PacketDecoder()
        parsed = decoder.decode_packet(eth_frame, packet_id=1, timestamp=1000.0)

        self.assertEqual(parsed.metadata.highest_protocol, "DNS")
        self.assertEqual(parsed.metadata.src_ip, "192.168.1.100")
        self.assertEqual(parsed.metadata.dst_ip, "8.8.8.8")
        self.assertEqual(len(parsed.layers), 4)  # Ethernet -> IPv4 -> UDP -> DNS


if __name__ == "__main__":
    unittest.main()

