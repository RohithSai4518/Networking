"""
Unit Tests for Threat & Anomaly Detection
"""

import unittest
from core.models import ParsedPacket, PacketMetadata, LayerInfo, ProtocolType
from core.security.detector import AnomalyDetector, calculate_entropy


class TestSecurityEngine(unittest.TestCase):

    def test_shannon_entropy(self):
        # Regular domain vs high-entropy domain
        normal_entropy = calculate_entropy("google")
        high_entropy = calculate_entropy("x8f19a0bc4e29d71fa9901")
        self.assertGreater(high_entropy, normal_entropy)

    def test_port_scan_detection(self):
        detector = AnomalyDetector()
        attacker_ip = "192.168.1.200"
        target_ip = "192.168.1.50"

        anomalies_triggered = []
        for port in range(20, 30):
            meta = PacketMetadata(
                id=port,
                timestamp=1000.0,
                length=64,
                highest_protocol="TCP",
                src_ip=attacker_ip,
                dst_ip=target_ip,
                src_port=50000 + port,
                dst_port=port,
                tcp_flags=["SYN"],
            )
            pkt = ParsedPacket(metadata=meta, layers=[], raw_hex="", payload_hex="", payload_text="")
            anoms = detector.analyze_packet(pkt)
            if anoms:
                anomalies_triggered.extend(anoms)

        self.assertGreater(len(anomalies_triggered), 0)
        self.assertEqual(anomalies_triggered[0].title, "Port Scan Activity Detected")

    def test_high_entropy_payload_detection(self):
        detector = AnomalyDetector()
        detector.high_entropy_threshold = 4.0
        random_text = "k9#mQ!2@vL$8*zP&5^wR(1)bN~4`eY+7-uI=3/oX" * 3
        meta = PacketMetadata(
            id=101,
            timestamp=1000.0,
            length=len(random_text),
            highest_protocol="TCP",
            src_ip="192.168.1.10",
            dst_ip="10.0.0.1",
        )
        pkt = ParsedPacket(
            metadata=meta,
            layers=[],
            raw_hex="aa" * 60,
            payload_hex="bb" * 60,
            payload_text=random_text,
        )
        anomalies = detector.analyze_packet(pkt)
        self.assertTrue(any(a.title == "High Entropy Payload Detected" for a in anomalies))

    def test_syn_flood_detection(self):
        detector = AnomalyDetector()
        detector.syn_flood_threshold = 5
        attacker = "192.168.1.99"
        target = "192.168.1.1"

        triggered = []
        for i in range(10):
            meta = PacketMetadata(
                id=200 + i,
                timestamp=1000.0 + i,
                length=64,
                highest_protocol="TCP",
                src_ip=attacker,
                dst_ip=target,
                tcp_flags=["SYN"],
            )
            pkt = ParsedPacket(metadata=meta, layers=[], raw_hex="", payload_hex="", payload_text="")
            anoms = detector.analyze_packet(pkt)
            if anoms:
                triggered.extend(anoms)

        self.assertTrue(any(a.title == "SYN Flood Attack Detected" for a in triggered))


if __name__ == "__main__":
    unittest.main()

