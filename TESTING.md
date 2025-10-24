# MCP Server Testing Guide

## Overview

This guide helps you test and diagnose the PDF Extraction MCP Server to isolate issues between the server and clients (like Forest Admin).

## Quick Start - Run Tests

### 1. Install Test Dependencies

```bash
pip install httpx httpx-sse psutil
```

### 2. Run the Test Script

Test against your Heroku deployment:

```bash
python test_mcp_client.py https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/mcp 20
```

Or test locally:

```bash
# Terminal 1: Start server
cd src
python -m pdf_extraction.http_server --port 8000

# Terminal 2: Run tests
python test_mcp_client.py http://localhost:8000/mcp 20
```

### 3. Check Health and Metrics

While the server is running, check its status:

```bash
# Health check
curl https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/health

# Detailed metrics
curl https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/metrics
```

## Understanding Test Results

### Success Indicators

✅ **100% success rate** = Server is working correctly
- If test script succeeds but Forest Admin fails → Forest Admin client issue
- Check Forest Admin's request frequency and session management

✅ **Consistent failures** = Identifiable server issue
- Check Heroku logs for error details
- Look for resource constraints (memory, CPU)
- Check temp file cleanup issues

### Failure Patterns

❌ **Every other request fails** = Session/state management issue
- Possible causes:
  - SSE connection not being reused properly
  - Session state corruption
  - Race condition in temp file handling

❌ **Random failures (no pattern)** = Resource or timing issue
- Possible causes:
  - Heroku dyno sleeping
  - Memory/CPU exhaustion
  - Network timeouts
  - OCR/Tesseract failures

❌ **First request fails, others succeed** = Initialization issue
- Cold start problems
- Missing dependencies on first run

## Monitoring Heroku Logs

Watch real-time logs while testing:

```bash
heroku logs --tail --app pdf-extraction-mcp-54041c60e7d7
```

Look for:
- Session connection/disconnection patterns
- Tool call timing and success/failure
- Error messages and stack traces
- Resource usage warnings

## Test Scenarios

### Scenario 1: Rapid Fire Test

Tests if the server handles quick successive requests:

```bash
python test_mcp_client.py https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/mcp 50
```

### Scenario 2: Different PDF URLs

Modify `test_mcp_client.py` to test with different PDFs:

```python
test_pdfs = [
    "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
    "https://example.com/other-pdf.pdf",
]
```

### Scenario 3: Large PDF Test

Test with a large multi-page PDF to check memory handling:

```python
result = await client.call_tool(
    "extract-pdf-contents",
    {"pdf_path": "https://example.com/large.pdf", "pages": None}  # All pages
)
```

## Interpreting Metrics

### Memory Usage

```json
{
  "resources": {
    "memory_rss_mb": 150.5,
    "memory_vms_mb": 350.2
  }
}
```

- **Normal**: RSS < 200 MB
- **Warning**: RSS > 300 MB (approaching Heroku limits)
- **Critical**: RSS > 450 MB (may cause dyno restart)

### CPU Usage

```json
{
  "resources": {
    "cpu_percent": 45.2
  }
}
```

- **Normal**: < 50% during extraction
- **Warning**: Sustained > 80%
- **Critical**: Sustained 100% (requests will queue)

### Success Rate

```json
{
  "requests": {
    "total": 100,
    "errors": 5,
    "success_rate": "95.0%"
  }
}
```

- **Excellent**: > 98%
- **Good**: 95-98%
- **Poor**: < 95% (investigate errors)

## Common Issues and Solutions

### Issue: "Every other request fails"

**Diagnosis**: Session state issue

**Solution**:
1. Check if Forest Admin is properly managing SSE connections
2. Verify session IDs are being passed correctly
3. Consider adding session persistence

### Issue: "Random timeouts"

**Diagnosis**: Resource exhaustion or cold starts

**Solution**:
1. Upgrade Heroku dyno tier
2. Optimize PDF processing (limit page count)
3. Add request queuing

### Issue: "OCR failures"

**Diagnosis**: Missing Tesseract language data

**Solution**:
```bash
# Check Heroku buildpack
heroku buildpacks --app pdf-extraction-mcp-54041c60e7d7

# Ensure tesseract buildpack is installed
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-apt
```

### Issue: "Temp file errors"

**Diagnosis**: File system issues or cleanup race conditions

**Solution**:
- Check logs for "Failed to clean up temp file" warnings
- Verify `/tmp` directory has space
- Add retry logic for file operations

## Advanced Debugging

### Enable Debug Logging

In `http_server.py`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Changed from INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Custom Test Script

Create custom tests for specific scenarios:

```python
# test_custom.py
import asyncio
from test_mcp_client import MCPTestClient

async def test_concurrent():
    """Test multiple concurrent clients"""
    clients = [MCPTestClient(server_url) for _ in range(5)]

    # Connect all clients
    await asyncio.gather(*[c.connect() for c in clients])

    # Run concurrent tool calls
    tasks = []
    for client in clients:
        for _ in range(10):
            tasks.append(client.call_tool("extract-pdf-contents", {...}))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Analyze results

asyncio.run(test_concurrent())
```

## Comparing with Forest Admin

### Forest Admin Test

1. Use Forest Admin to call the tool 20 times
2. Document which attempts fail
3. Note the failure pattern

### Direct Test

1. Run `test_mcp_client.py` with same parameters
2. Compare failure patterns

### Analysis

| Scenario | Forest Admin | Test Script | Conclusion |
|----------|-------------|-------------|------------|
| Both fail with same pattern | ✗ | ✗ | Server issue |
| Forest fails, script succeeds | ✗ | ✓ | Forest Admin issue |
| Script fails, Forest succeeds | ✓ | ✗ | Test script issue |
| Both succeed | ✓ | ✓ | No issue found |

## Getting Help

If tests reveal issues:

1. Save test output:
   ```bash
   python test_mcp_client.py ... > test_results.txt 2>&1
   ```

2. Save metrics:
   ```bash
   curl https://.../metrics > metrics.json
   ```

3. Save logs:
   ```bash
   heroku logs --tail > heroku_logs.txt
   ```

4. Share these files for diagnosis

## Next Steps

After identifying the issue:

- **Server issue**: Fix in `http_server.py` or `pdf_extractor.py`, redeploy
- **Forest Admin issue**: Report to Forest Admin support with test results
- **Infrastructure issue**: Upgrade Heroku dyno or optimize resources
