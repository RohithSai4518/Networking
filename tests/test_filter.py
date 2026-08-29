"""
Unit Tests for Query and Filter Engine
"""

import unittest
from core.models import ParsedPacket, PacketMetadata, LayerInfo, ProtocolType
from core.storage.filter import FilterEngine


class TestFilterEngine(unittest.TestCase):

    def setUp(self):
        self.engine = FilterEngine()
        self.meta = PacketMetadata(
            id=10,
            timestamp=100.0,
            length=1500,
            highest_protocol="HTTP",
            src_ip="192.168.1.100",
            dst_ip="93.184.216.34",
            src_port=49152,
            dst_port=80,
            info="GET /index.html HTTP/1.1",
        )
        layer_http = LayerInfo(
            layer_name="Hypertext Transfer Protocol",
            protocol=ProtocolType.HTTP,
            offset=54,
            length=1446,
        )
        self.packet = ParsedPacket(
            metadata=self.meta,
            layers=[layer_http],
            raw_hex="",
            payload_hex="",
            payload_text="GET /index.html HTTP/1.1 Host: example.com",
        )

    def test_protocol_filter(self):
        self.assertTrue(self.engine.evaluate(self.packet, "http"))
        self.assertFalse(self.engine.evaluate(self.packet, "dns"))

    def test_ip_and_port_expression(self):
        self.assertTrue(self.engine.evaluate(self.packet, "ip.src == '192.168.1.100'"))
        self.assertTrue(self.engine.evaluate(self.packet, "dst_port == 80"))
        self.assertTrue(self.engine.evaluate(self.packet, "ip.src == '192.168.1.100' and dst_port == 80"))
        self.assertFalse(self.engine.evaluate(self.packet, "ip.src == '10.0.0.1' or dst_port == 443"))

    def test_payload_contains(self):
        self.assertTrue(self.engine.evaluate(self.packet, "payload contains 'example.com'"))
        self.assertFalse(self.engine.evaluate(self.packet, "payload contains 'secret_token'"))


if __name__ == "__main__":
    unittest.main()
