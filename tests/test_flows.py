"""
Unit Tests for Flow Tracking and Stream Reassembly
"""

import unittest
from core.models import ParsedPacket, PacketMetadata, LayerInfo, ProtocolType
from core.flows.tracker import FlowTracker
from core.flows.reassembly import TcpStreamReassembler


class TestFlowsEngine(unittest.TestCase):

    def test_tcp_stream_reassembly(self):
        reassembler = TcpStreamReassembler(initial_seq=100)
        # Out of order delivery: segment 2 arrives before segment 1
        reassembler.add_segment(seq=105, payload=b" World!")
        reassembler.add_segment(seq=100, payload=b"Hello")

        reconstructed = reassembler.get_text_preview()
        self.assertEqual(reconstructed, "Hello World!")

    def test_flow_tracker_packet_processing(self):
        tracker = FlowTracker()

        meta = PacketMetadata(
            id=1,
            timestamp=100.0,
            length=64,
            highest_protocol="TCP",
            src_ip="192.168.1.10",
            dst_ip="8.8.8.8",
            src_port=54321,
            dst_port=443,
        )
        packet = ParsedPacket(metadata=meta, layers=[], raw_hex="", payload_hex="", payload_text="")

        flow = tracker.process_packet(packet)
        self.assertIsNotNone(flow)
        self.assertEqual(flow.total_packets, 1)
        self.assertEqual(flow.total_bytes, 64)
        self.assertEqual(len(tracker.flows), 1)


if __name__ == "__main__":
    unittest.main()
