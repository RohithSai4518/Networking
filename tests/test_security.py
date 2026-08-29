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


if __name__ == "__main__":
    unittest.main()
