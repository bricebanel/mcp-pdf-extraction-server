#!/usr/bin/env python3
"""
Simple MCP Test - Direct HTTP testing without full SSE complexity
"""

import httpx
import json
import sys
from datetime import datetime


def timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


async def test_health(base_url: str):
    """Test health endpoint"""
    print(f"\n[{timestamp()}] Testing health endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/health")
        print(f"[{timestamp()}] Status: {response.status_code}")
        if response.status_code == 200:
            print(f"[{timestamp()}] Response: {json.dumps(response.json(), indent=2)}")
            return True
        return False


async def test_metrics(base_url: str):
    """Test metrics endpoint"""
    print(f"\n[{timestamp()}] Testing metrics endpoint...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/metrics")
        print(f"[{timestamp()}] Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"[{timestamp()}] Server uptime: {data['server']['uptime_seconds']:.1f}s")
            print(f"[{timestamp()}] Active sessions: {data['sessions']['active']}")
            print(f"[{timestamp()}] Total requests: {data['requests']['total']}")
            print(f"[{timestamp()}] Success rate: {data['requests']['success_rate']}")
            print(f"[{timestamp()}] Memory RSS: {data['resources']['memory_rss_mb']:.1f} MB")
            return True
        return False


async def test_sse_connection(base_url: str):
    """Test basic SSE connection"""
    print(f"\n[{timestamp()}] Testing SSE connection...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(
                f"{base_url}/mcp",
                headers={"Accept": "text/event-stream"}
            )
            print(f"[{timestamp()}] Status: {response.status_code}")
            print(f"[{timestamp()}] Content-Type: {response.headers.get('content-type')}")

            if response.status_code == 200:
                # Read first few lines
                lines = []
                async for line in response.aiter_lines():
                    lines.append(line)
                    print(f"[{timestamp()}] SSE: {line}")
                    if len(lines) >= 5:
                        break
                return True
            return False
        except Exception as e:
            print(f"[{timestamp()}] ✗ Error: {e}")
            return False


async def main():
    if len(sys.argv) > 1:
        base_url = sys.argv[1].rstrip('/mcp').rstrip('/sse')
    else:
        base_url = "https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com"

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║         Simple MCP Server Connection Test                    ║
╚══════════════════════════════════════════════════════════════╝

Base URL: {base_url}
Start time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
""")

    # Test endpoints
    health_ok = await test_health(base_url)
    metrics_ok = await test_metrics(base_url)
    sse_ok = await test_sse_connection(base_url)

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Health endpoint:  {'✓ PASS' if health_ok else '✗ FAIL'}")
    print(f"Metrics endpoint: {'✓ PASS' if metrics_ok else '✗ FAIL'}")
    print(f"SSE connection:   {'✓ PASS' if sse_ok else '✗ FAIL'}")
    print("="*70)

    return 0 if all([health_ok, metrics_ok, sse_ok]) else 1


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
