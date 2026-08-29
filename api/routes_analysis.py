"""
NetLens Pro - Analytical & Metrics API Routes
Provides endpoints for network traffic analysis, statistics, and metrics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


class TrafficMetrics(BaseModel):
    """Traffic metrics model."""
    total_packets: int
    total_bytes: int
    packets_per_second: float
    bytes_per_second: float
    mbps: float
    unique_sources: int
    unique_destinations: int
    protocol_distribution: Dict[str, int]


class ProtocolMetrics(BaseModel):
    """Protocol-specific metrics."""
    protocol: str
    packet_count: int
    byte_count: int
    avg_packet_size: float
    percentage: float


class TimeSeriesData(BaseModel):
    """Time series data for metrics."""
    timestamp: datetime
    value: float
    metric_type: str


class AnomalySummary(BaseModel):
    """Security anomaly summary."""
    total_anomalies: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    recent_anomalies: List[Dict[str, Any]]


class FlowMetrics(BaseModel):
    """Network flow metrics."""
    active_flows: int
    total_flows: int
    avg_flow_duration: float
    top_talkers: List[Dict[str, Any]]
    top_protocols: List[Dict[str, Any]]


class AnalysisModule:
    """Analytical & Metrics API Routes Component Module."""
    
    def __init__(self):
        self.ready = True
        self.packet_cache: List[Dict[str, Any]] = []
        self.metrics_cache: Dict[str, Any] = {}
        self.last_update: Optional[datetime] = None
    
    def process_request(self) -> Dict[str, Any]:
        """Process incoming analysis request."""
        return {"status": "ok", "ready": self.ready}
    
    def update_metrics(self, packet_data: Dict[str, Any]):
        """Update metrics with new packet data."""
        self.packet_cache.append(packet_data)
        if len(self.packet_cache) > 10000:  # Keep last 10k packets
            self.packet_cache = self.packet_cache[-10000:]
        self.last_update = datetime.now()
    
    def calculate_traffic_metrics(self) -> TrafficMetrics:
        """Calculate real-time traffic metrics."""
        if not self.packet_cache:
            return TrafficMetrics(
                total_packets=0,
                total_bytes=0,
                packets_per_second=0.0,
                bytes_per_second=0.0,
                mbps=0.0,
                unique_sources=0,
                unique_destinations=0,
                protocol_distribution={}
            )
        
        total_packets = len(self.packet_cache)
        total_bytes = sum(p.get('size', 0) for p in self.packet_cache)
        
        # Calculate rates if we have timestamp data
        time_span = 60.0  # Default to 1 minute
        if self.last_update:
            oldest_packet = min(p.get('timestamp', datetime.now()) for p in self.packet_cache)
            time_span = max((self.last_update - oldest_packet).total_seconds(), 1.0)
        
        packets_per_second = total_packets / time_span
        bytes_per_second = total_bytes / time_span
        mbps = (bytes_per_second * 8) / 1_000_000
        
        # Calculate unique IPs
        unique_sources = len(set(p.get('src_ip') for p in self.packet_cache if p.get('src_ip')))
        unique_destinations = len(set(p.get('dst_ip') for p in self.packet_cache if p.get('dst_ip')))
        
        # Protocol distribution
        protocol_dist = {}
        for packet in self.packet_cache:
            protocol = packet.get('protocol', 'Unknown')
            protocol_dist[protocol] = protocol_dist.get(protocol, 0) + 1
        
        return TrafficMetrics(
            total_packets=total_packets,
            total_bytes=total_bytes,
            packets_per_second=packets_per_second,
            bytes_per_second=bytes_per_second,
            mbps=mbps,
            unique_sources=unique_sources,
            unique_destinations=unique_destinations,
            protocol_distribution=protocol_dist
        )
    
    def get_protocol_metrics(self, protocol: str) -> ProtocolMetrics:
        """Get metrics for a specific protocol."""
        protocol_packets = [p for p in self.packet_cache if p.get('protocol') == protocol]
        
        if not protocol_packets:
            return ProtocolMetrics(
                protocol=protocol,
                packet_count=0,
                byte_count=0,
                avg_packet_size=0.0,
                percentage=0.0
            )
        
        packet_count = len(protocol_packets)
        byte_count = sum(p.get('size', 0) for p in protocol_packets)
        avg_packet_size = byte_count / packet_count if packet_count > 0 else 0.0
        percentage = (packet_count / len(self.packet_cache)) * 100 if self.packet_cache else 0.0
        
        return ProtocolMetrics(
            protocol=protocol,
            packet_count=packet_count,
            byte_count=byte_count,
            avg_packet_size=avg_packet_size,
            percentage=percentage
        )
    
    def get_time_series_metrics(self, metric_type: str, hours: int = 24) -> List[TimeSeriesData]:
        """Get time series data for a specific metric."""
        # This would typically query a database or time-series store
        # For now, return mock data
        now = datetime.now()
        data = []
        
        for i in range(hours):
            timestamp = now - timedelta(hours=i)
            # Mock data - in production, this would be real metrics
            value = 100.0 + (i * 10.0)  # Mock trend
            data.append(TimeSeriesData(
                timestamp=timestamp,
                value=value,
                metric_type=metric_type
            ))
        
        return data
    
    def get_anomaly_summary(self) -> AnomalySummary:
        """Get summary of detected security anomalies."""
        # This would typically query the security module
        # For now, return mock data
        return AnomalySummary(
            total_anomalies=0,
            critical_count=0,
            high_count=0,
            medium_count=0,
            low_count=0,
            recent_anomalies=[]
        )
    
    def get_flow_metrics(self) -> FlowMetrics:
        """Get network flow metrics."""
        # This would typically query the flow tracking module
        # For now, return mock data
        return FlowMetrics(
            active_flows=0,
            total_flows=0,
            avg_flow_duration=0.0,
            top_talkers=[],
            top_protocols=[]
        )


# Global analysis module instance
analysis_module = AnalysisModule()


@router.get("/metrics", response_model=TrafficMetrics)
async def get_traffic_metrics():
    """Get current traffic metrics."""
    return analysis_module.calculate_traffic_metrics()


@router.get("/protocol/{protocol}", response_model=ProtocolMetrics)
async def get_protocol_specific_metrics(protocol: str):
    """Get metrics for a specific protocol."""
    return analysis_module.get_protocol_metrics(protocol)


@router.get("/timeseries/{metric_type}")
async def get_time_series(metric_type: str, hours: int = Query(24, ge=1, le=168)):
    """Get time series data for a specific metric."""
    return analysis_module.get_time_series_metrics(metric_type, hours)


@router.get("/anomalies", response_model=AnomalySummary)
async def get_anomaly_summary():
    """Get summary of security anomalies."""
    return analysis_module.get_anomaly_summary()


@router.get("/flows", response_model=FlowMetrics)
async def get_flow_metrics():
    """Get network flow metrics."""
    return analysis_module.get_flow_metrics()


@router.get("/top-talkers")
async def get_top_talkers(limit: int = Query(10, ge=1, le=100)):
    """Get top talkers by traffic volume."""
    if not analysis_module.packet_cache:
        return []
    
    # Calculate traffic per IP
    ip_traffic = {}
    for packet in analysis_module.packet_cache:
        src_ip = packet.get('src_ip')
        if src_ip:
            ip_traffic[src_ip] = ip_traffic.get(src_ip, 0) + packet.get('size', 0)
    
    # Sort and return top talkers
    sorted_ips = sorted(ip_traffic.items(), key=lambda x: x[1], reverse=True)
    return [{"ip": ip, "bytes": bytes_} for ip, bytes_ in sorted_ips[:limit]]


@router.get("/bandwidth")
async def get_bandwidth_usage():
    """Get current bandwidth usage statistics."""
    metrics = analysis_module.calculate_traffic_metrics()
    return {
        "current_mbps": metrics.mbps,
        "peak_mbps": metrics.mbps * 1.5,  # Mock peak
        "average_mbps": metrics.mbps * 0.8,  # Mock average
        "utilization_percent": (metrics.mbps / 1000.0) * 100 if metrics.mbps > 0 else 0.0
    }


@router.get("/protocols")
async def get_protocol_distribution():
    """Get protocol distribution statistics."""
    metrics = analysis_module.calculate_traffic_metrics()
    return metrics.protocol_distribution


@router.post("/reset")
async def reset_analysis():
    """Reset analysis cache and metrics."""
    analysis_module.packet_cache = []
    analysis_module.metrics_cache = {}
    analysis_module.last_update = None
    return {"status": "success", "message": "Analysis cache reset"}


@router.get("/health")
async def health_check():
    """Health check endpoint for analysis module."""
    return {
        "status": "healthy",
        "module": "analysis",
        "ready": analysis_module.ready,
        "cached_packets": len(analysis_module.packet_cache),
        "last_update": analysis_module.last_update
    }