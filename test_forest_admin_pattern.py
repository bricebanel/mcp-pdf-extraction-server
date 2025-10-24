#!/usr/bin/env python3
"""
Test that mimics Forest Admin's exact behavior
This helps reproduce the "first attempt fails, second succeeds" pattern
"""

import asyncio
import httpx
import json
from datetime import datetime
import sys


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {msg}")


async def test_single_connection_multiple_calls(base_url: str, num_calls: int = 5):
    """
    Mimic Forest Admin: Open ONE SSE connection, send multiple tool calls
    """
    log(f"Starting test: {num_calls} tool calls on single SSE connection")

    sse_url = f"{base_url}/mcp"
    messages_url = f"{base_url}/messages"

    session_id = None
    request_id = 0
    results = []

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            # Step 1: Open SSE connection
            log("Opening SSE connection...")

            async with client.stream("GET", sse_url, headers={"Accept": "text/event-stream"}) as response:
                if response.status_code != 200:
                    log(f"✗ Failed to open SSE: HTTP {response.status_code}")
                    return results

                log(f"✓ SSE connection established (HTTP {response.status_code})")

                # Step 2: Read SSE endpoint event to get session ID
                log("Reading SSE stream for session ID...")

                event_type = None
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                        log(f"  SSE event type: {event_type}")
                    elif line.startswith("data:") and event_type == "endpoint":
                        data = line.split(":", 1)[1].strip()
                        log(f"  SSE endpoint data: {data}")

                        if "session_id=" in data:
                            session_id = data.split("session_id=")[1].split()[0]
                            log(f"✓ Got session ID: {session_id}")
                            break

                if not session_id:
                    log("✗ No session ID received")
                    return results

                # Step 3: Send initialize request
                log("\nSending initialize request...")
                request_id += 1
                init_request = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-03-26",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "forest_admin_test",
                            "version": "1.0.0"
                        }
                    }
                }

                init_response = await client.post(
                    f"{messages_url}?session_id={session_id}",
                    json=init_request,
                    headers={"Content-Type": "application/json"}
                )

                if init_response.status_code != 200:
                    log(f"✗ Initialize failed: HTTP {init_response.status_code}")
                    log(f"  Response: {init_response.text}")
                    return results

                init_result = init_response.json()
                if "error" in init_result:
                    log(f"✗ Initialize error: {init_result['error']}")
                    return results

                log(f"✓ Initialized successfully")
                log(f"  Server: {init_result.get('result', {}).get('serverInfo', {}).get('name')}")

                # Step 4: List tools
                log("\nListing tools...")
                request_id += 1
                list_request = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "method": "tools/list",
                    "params": {}
                }

                list_response = await client.post(
                    f"{messages_url}?session_id={session_id}",
                    json=list_request,
                    headers={"Content-Type": "application/json"}
                )

                if list_response.status_code != 200:
                    log(f"✗ List tools failed: HTTP {list_response.status_code}")
                    return results

                list_result = list_response.json()
                if "error" in list_result:
                    log(f"✗ List tools error: {list_result['error']}")
                    return results

                tools = list_result.get("result", {}).get("tools", [])
                log(f"✓ Found {len(tools)} tool(s)")
                for tool in tools:
                    log(f"  - {tool['name']}")

                # Step 5: Call tool multiple times
                log(f"\n{'='*70}")
                log(f"Starting {num_calls} consecutive tool calls...")
                log(f"{'='*70}\n")

                test_pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

                for i in range(num_calls):
                    request_id += 1

                    log(f"Call {i+1}/{num_calls}...")

                    call_request = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "method": "tools/call",
                        "params": {
                            "name": "extract-pdf-contents",
                            "arguments": {
                                "pdf_path": test_pdf_url,
                                "pages": "1"
                            }
                        }
                    }

                    start_time = asyncio.get_event_loop().time()

                    call_response = await client.post(
                        f"{messages_url}?session_id={session_id}",
                        json=call_request,
                        headers={"Content-Type": "application/json"},
                        timeout=60.0
                    )

                    duration = asyncio.get_event_loop().time() - start_time

                    success = False
                    error_msg = None

                    if call_response.status_code != 200:
                        error_msg = f"HTTP {call_response.status_code}: {call_response.text[:100]}"
                    else:
                        call_result = call_response.json()
                        if "error" in call_result:
                            error_msg = f"{call_result['error'].get('message', 'Unknown error')}"
                        else:
                            success = True
                            content = call_result.get("result", {})
                            content_length = len(str(content))

                    results.append({
                        "call_num": i + 1,
                        "success": success,
                        "duration": duration,
                        "error": error_msg
                    })

                    if success:
                        log(f"  ✓ Success ({duration:.2f}s)")
                    else:
                        log(f"  ✗ Failed: {error_msg}")

                    # Small delay between calls (like Forest Admin might do)
                    await asyncio.sleep(0.5)

                log(f"\n{'='*70}")
                log("Test complete - disconnecting SSE")
                log(f"{'='*70}")

    except Exception as e:
        log(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

    return results


async def test_multiple_connections(base_url: str, num_connections: int = 5):
    """
    Test with multiple separate SSE connections (like if Forest Admin reconnects each time)
    """
    log(f"\n{'='*70}")
    log(f"Testing {num_connections} separate SSE connections")
    log(f"{'='*70}\n")

    results = []

    for i in range(num_connections):
        log(f"\n--- Connection {i+1}/{num_connections} ---")

        # Each iteration opens a NEW SSE connection
        conn_results = await test_single_connection_multiple_calls(base_url, num_calls=1)

        if conn_results:
            results.extend(conn_results)

        await asyncio.sleep(1)  # Pause between connections

    return results


def print_summary(results, test_name):
    """Print test results summary"""
    print(f"\n{'='*70}")
    print(f"RESULTS: {test_name}")
    print(f"{'='*70}")

    if not results:
        print("No results collected")
        return

    total = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total - successful

    print(f"\nTotal calls: {total}")
    print(f"Successful:  {successful} ({successful/total*100:.1f}%)")
    print(f"Failed:      {failed} ({failed/total*100:.1f}%)")

    if total > 0:
        avg_duration = sum(r["duration"] for r in results) / total
        print(f"Avg duration: {avg_duration:.2f}s")

    # Check for patterns
    if failed > 0:
        print("\nFailure Analysis:")
        failure_indices = [r["call_num"] for r in results if not r["success"]]
        print(f"Failed on calls: {failure_indices}")

        # Check if first call always fails
        first_calls = [r for r in results if r["call_num"] == 1]
        first_failures = sum(1 for r in first_calls if not r["success"])
        if first_failures > 0:
            print(f"⚠️  First call failed {first_failures}/{len(first_calls)} times")

        # Check for every-other pattern
        if len(failure_indices) > 1:
            differences = [failure_indices[i+1] - failure_indices[i] for i in range(len(failure_indices)-1)]
            if len(set(differences)) == 1:
                print(f"⚠️  PATTERN: Failures every {differences[0]} calls")

    print("\nDetailed Results:")
    print("-" * 70)
    for r in results:
        status = "✓" if r["success"] else "✗"
        print(f"{r['call_num']:3}. {status} ({r['duration']:.2f}s)", end="")
        if r["error"]:
            print(f" - {r['error']}")
        else:
            print()

    print("=" * 70)


async def main():
    if len(sys.argv) > 1:
        base_url = sys.argv[1].rstrip('/mcp').rstrip('/sse')
    else:
        base_url = "https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com"

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║       Forest Admin Pattern Test                              ║
╚══════════════════════════════════════════════════════════════╝

Server: {base_url}
Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

This test mimics Forest Admin's behavior:
1. Open ONE SSE connection
2. Initialize
3. List tools
4. Call tool multiple times on same connection
""")

    # Test 1: Single connection, multiple calls (normal Forest Admin behavior)
    results1 = await test_single_connection_multiple_calls(base_url, num_calls=10)
    print_summary(results1, "Single Connection - 10 Calls")

    # Test 2: Multiple connections (if Forest Admin reconnects each time)
    results2 = await test_multiple_connections(base_url, num_connections=10)
    print_summary(results2, "Multiple Connections - 1 Call Each")

    # Overall summary
    all_results = results1 + results2
    total_failures = sum(1 for r in all_results if not r["success"])

    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
