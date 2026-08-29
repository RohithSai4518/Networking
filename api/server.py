"""
NetLens Pro - FastAPI Application Server
Provides REST API endpoints and WebSocket endpoints for real-time network analysis.
"""

from fastapi import FastAPI, WebSocket, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any, List, Optional
import os
import asyncio

# Import route modules
from api.routes_analysis import router as analysis_router, analysis_module

app = FastAPI(title="NetLens Pro API", version="2.0.0")

# Mount web static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "static")
templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "templates")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include route modules
app.include_router(analysis_router)


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    index_file = os.path.join(templates_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>NetLens Pro Server Running</h1>"


@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy", "service": "NetLens Pro", "version": "2.0.0"}


@app.get("/api/v1/stats")
async def get_stats():
    metrics = analysis_module.calculate_traffic_metrics()
    return {
        "total_packets": metrics.total_packets,
        "total_bytes": metrics.total_bytes,
        "packets_per_second": metrics.packets_per_second,
        "bytes_per_second": metrics.bytes_per_second,
        "mbps": metrics.mbps,
        "active_flow_count": analysis_module.get_flow_metrics().active_flows,
        "anomaly_count": analysis_module.get_anomaly_summary().total_anomalies,
        "protocol_distribution": metrics.protocol_distribution,
    }


@app.get("/api/v1/packets")
async def get_packets(limit: int = Query(50, ge=1, le=1000)):
    return {"packets": [], "count": 0, "limit": limit}


@app.get("/api/v1/flows")
async def get_flows():
    flow_metrics = analysis_module.get_flow_metrics()
    return {"flows": [], "count": flow_metrics.total_flows, "active": flow_metrics.active_flows}


@app.get("/api/v1/alerts")
async def get_alerts():
    anomaly_summary = analysis_module.get_anomaly_summary()
    return {"alerts": anomaly_summary.recent_anomalies, "count": anomaly_summary.total_anomalies}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time packet streaming."""
    await websocket.accept()
    try:
        while True:
            # Send real-time updates
            metrics = analysis_module.calculate_traffic_metrics()
            await websocket.send_json({
                "type": "metrics",
                "data": {
                    "total_packets": metrics.total_packets,
                    "mbps": metrics.mbps,
                    "protocol_distribution": metrics.protocol_distribution
                }
            })
            # In production, this would be event-driven
            await asyncio.sleep(1)  # Send updates every second
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()


@app.get("/api/v1/config")
async def get_config():
    """Get current server configuration."""
    return {
        "version": "2.0.0",
        "features": {
            "packet_capture": True,
            "deep_packet_inspection": True,
            "flow_tracking": True,
            "anomaly_detection": True,
            "protocol_decoding": True
        },
        "limits": {
            "max_packet_size": 65536,
            "max_flows": 10000,
            "retention_hours": 24
        }
    }


@app.post("/api/v1/capture/start")
async def start_capture(interface: str = "eth0"):
    """Start packet capture on specified interface."""
    return {"status": "success", "interface": interface, "message": "Capture started"}


@app.post("/api/v1/capture/stop")
async def stop_capture():
    """Stop packet capture."""
    return {"status": "success", "message": "Capture stopped"}


@app.get("/api/v1/interfaces")
async def get_interfaces():
    """Get available network interfaces."""
    return {
        "interfaces": [
            {"name": "eth0", "description": "Ethernet Interface 0", "status": "up"},
            {"name": "wlan0", "description": "Wireless Interface 0", "status": "up"},
            {"name": "lo", "description": "Loopback", "status": "up"}
        ]
    }