#!/usr/bin/env python3
"""
MCP Client Test Script

Tests the MCP server directly to isolate server vs client issues.
Runs multiple consecutive tool calls and tracks success/failure patterns.
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional
import httpx
from httpx_sse import aconnect_sse


class MCPTestClient:
    """Test client for MCP server using SSE transport"""

    def __init__(self, server_url: str):
        self.server_url = server_url
        self.base_url = server_url.rstrip('/mcp').rstrip('/sse')
        self.session_id: Optional[str] = None
        self.sse_url = f"{self.base_url}/mcp"
        self.messages_url = f"{self.base_url}/messages"
        self.request_id = 0
        self.results: List[Dict] = []

    def get_next_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id

    async def connect(self) -> bool:
        """Establish SSE connection and initialize"""
        try:
            print(f"[{self.timestamp()}] Connecting to {self.sse_url}...")

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                # First, open the SSE connection
                response = await client.get(
                    self.sse_url,
                    headers={"Accept": "text/event-stream"},
                    timeout=httpx.Timeout(5.0, read=None)  # No read timeout for streaming
                )

                # Check if we got redirected or if content-type is correct
                print(f"[{self.timestamp()}] Response status: {response.status_code}")
                print(f"[{self.timestamp()}] Content-Type: {response.headers.get('content-type')}")

                if response.status_code != 200:
                    print(f"[{self.timestamp()}] ✗ Failed to establish SSE connection")
                    return False

                # Parse SSE stream manually
                async for line in response.aiter_lines():
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                        if event_type == "endpoint":
                            # Next line should be data
                            continue
                    elif line.startswith("data:"):
                        data = line.split(":", 1)[1].strip()
                        print(f"[{self.timestamp()}] Received endpoint: {data}")

                        # Extract session ID from endpoint URL
                        if "session_id=" in data:
                            self.session_id = data.split("session_id=")[1].split("&")[0].split()[0]
                            print(f"[{self.timestamp()}] Session ID: {self.session_id}")
                            break

            # Now send initialize request
            if self.session_id:
                init_result = await self.send_request(
                    "initialize",
                    {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "test_client",
                            "version": "1.0.0"
                        }
                    }
                )
                if init_result:
                    print(f"[{self.timestamp()}] ✓ Initialized successfully")
                    return True
                else:
                    print(f"[{self.timestamp()}] ✗ Initialization failed")
                    return False
            else:
                print(f"[{self.timestamp()}] ✗ No session ID received")
                return False

        except Exception as e:
            print(f"[{self.timestamp()}] ✗ Connection failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def send_request(self, method: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Send a JSON-RPC request via POST"""
        request_id = self.get_next_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
        }
        if params is not None:
            request["params"] = params

        url = f"{self.messages_url}?session_id={self.session_id}"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    json=request,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    if "error" in result:
                        print(f"[{self.timestamp()}] ✗ Error response: {result['error']}")
                        return None
                    return result.get("result")
                else:
                    print(f"[{self.timestamp()}] ✗ HTTP {response.status_code}: {response.text}")
                    return None
        except Exception as e:
            print(f"[{self.timestamp()}] ✗ Request failed: {e}")
            return None

    async def list_tools(self) -> Optional[List]:
        """List available tools"""
        result = await self.send_request("tools/list", {})
        if result and "tools" in result:
            return result["tools"]
        return None

    async def call_tool(self, name: str, arguments: Dict) -> Optional[Dict]:
        """Call a tool"""
        start_time = datetime.now()

        result = await self.send_request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments
            }
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Record result
        test_result = {
            "timestamp": self.timestamp(),
            "tool": name,
            "arguments": arguments,
            "duration": duration,
            "success": result is not None,
            "error": None if result else "No result returned"
        }

        if result and "content" in result:
            test_result["content_length"] = len(str(result["content"]))

        self.results.append(test_result)

        return result

    @staticmethod
    def timestamp() -> str:
        """Get current timestamp string"""
        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*80)
        print("TEST RESULTS SUMMARY")
        print("="*80)

        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        failed = total - successful

        print(f"\nTotal tests: {total}")
        print(f"Successful: {successful} ({successful/total*100:.1f}%)")
        print(f"Failed: {failed} ({failed/total*100:.1f}%)")

        if total > 0:
            avg_duration = sum(r["duration"] for r in self.results) / total
            print(f"Average duration: {avg_duration:.2f}s")

        # Check for patterns
        if failed > 0:
            print("\nFailure Pattern Analysis:")
            failure_indices = [i for i, r in enumerate(self.results) if not r["success"]]
            print(f"Failed test indices: {failure_indices}")

            # Check if it's every other
            if len(failure_indices) > 1:
                differences = [failure_indices[i+1] - failure_indices[i] for i in range(len(failure_indices)-1)]
                if len(set(differences)) == 1 and differences[0] == 2:
                    print("⚠️  PATTERN DETECTED: Every other request fails!")
                elif len(set(differences)) == 1:
                    print(f"⚠️  PATTERN DETECTED: Every {differences[0]} requests, one fails!")

        print("\nDetailed Results:")
        print("-" * 80)
        for i, result in enumerate(self.results, 1):
            status = "✓" if result["success"] else "✗"
            print(f"{i}. [{result['timestamp']}] {status} {result['tool']} "
                  f"({result['duration']:.2f}s)")
            if not result["success"]:
                print(f"   Error: {result['error']}")

        print("="*80)


async def run_tests(server_url: str, num_tests: int = 20):
    """Run comprehensive tests"""
    client = MCPTestClient(server_url)

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║              MCP Server Test Suite                           ║
╚══════════════════════════════════════════════════════════════╝

Server URL: {server_url}
Number of tests: {num_tests}
Start time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

""")

    # Connect and initialize
    if not await client.connect():
        print("Failed to connect to server. Exiting.")
        return

    print(f"\n[{client.timestamp()}] Connected successfully\n")
    await asyncio.sleep(1)

    # List tools
    print(f"[{client.timestamp()}] Listing tools...")
    tools = await client.list_tools()
    if tools:
        print(f"[{client.timestamp()}] ✓ Found {len(tools)} tool(s):")
        for tool in tools:
            print(f"   - {tool.get('name')}: {tool.get('description', 'No description')[:60]}...")
    else:
        print(f"[{client.timestamp()}] ✗ Failed to list tools")
        return

    await asyncio.sleep(1)

    # Run multiple tool calls with a simple test PDF
    print(f"\n[{client.timestamp()}] Starting {num_tests} consecutive tool calls...")
    print(f"{'='*80}\n")

    # Test with a real PDF URL (using a sample PDF)
    test_pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

    for i in range(num_tests):
        print(f"[{client.timestamp()}] Test {i+1}/{num_tests}...", end=" ")

        result = await client.call_tool(
            "extract-pdf-contents",
            {
                "pdf_path": test_pdf_url,
                "pages": "1"
            }
        )

        if result:
            print("✓")
        else:
            print("✗")

        # Small delay between requests
        await asyncio.sleep(0.5)

    # Print summary
    client.print_summary()

    # Return exit code based on results
    failures = sum(1 for r in client.results if not r["success"])
    return 0 if failures == 0 else 1


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        server_url = sys.argv[1]
    else:
        server_url = "https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/mcp"

    num_tests = 20
    if len(sys.argv) > 2:
        num_tests = int(sys.argv[2])

    try:
        exit_code = asyncio.run(run_tests(server_url, num_tests))
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
