"""
Unit Tests for Custom PCAP Reader and Writer
"""

import io
import unittest
from core.capture.pcap import PcapWriter, PcapReader
from core.capture.generator import build_ethernet_header, build_ipv4_header, build_udp_datagram


class TestPcapEngine(unittest.TestCase):

    def test_pcap_write_and_read_roundtrip(self):
        buf = io.BytesIO()
        writer = PcapWriter(buf)

        # Generate sample packet
        udp = build_udp_datagram(1234, 5678, b"PCAP Payload Test")
        ip = build_ipv4_header("10.0.0.1", "10.0.0.2", 17, len(udp)) + udp
        eth = build_ethernet_header("00:11:22:33:44:55", "AA:BB:CC:DD:EE:FF", 0x0800) + ip

        pkt1_ts = 1700000000.123456
        writer.write_packet(eth, pkt1_ts)

        # Read back
        buf.seek(0)
        reader = PcapReader(buf)
        packets = reader.read_packets()

        self.assertEqual(len(packets), 1)
        ts, read_bytes = packets[0]
        self.assertAlmostEqual(ts, pkt1_ts, places=4)
        self.assertEqual(read_bytes, eth)

    def test_multiple_packets_roundtrip(self):
        buf = io.BytesIO()
        writer = PcapWriter(buf)

        sample_packets = [
            (1700000001.0, b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\x08\x00" + b"Packet 1"),
            (1700000002.5, b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\x08\x00" + b"Packet 2"),
            (1700000003.9, b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xaa\xbb\x08\x00" + b"Packet 3"),
        ]

        for ts, pkt_data in sample_packets:
            writer.write_packet(pkt_data, ts)

        buf.seek(0)
        reader = PcapReader(buf)
        read_back = reader.read_packets()

        self.assertEqual(len(read_back), 3)
        for i, (ts, pkt_data) in enumerate(sample_packets):
            self.assertAlmostEqual(read_back[i][0], ts, places=3)
            self.assertEqual(read_back[i][1], pkt_data)


if __name__ == "__main__":
    unittest.main()

