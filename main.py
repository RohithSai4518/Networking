"""
NetLens Pro - Main Application Entrypoint
Starts the Uvicorn ASGI Server serving the FastAPI backend and Web Dashboard.
"""

import os
import sys
import uvicorn


def main():
    port = int(os.environ.get("PORT", 8088))
    host = os.environ.get("HOST", "127.0.0.1")

    print("=" * 70)
    print("  NETLENS PRO - Full-Stack Network Protocol Analyzer & DPI Suite")
    print(f"  Live Web Dashboard: http://{host}:{port}")
    print("=" * 70)
    
    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
