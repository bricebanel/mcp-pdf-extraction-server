# Testing Infrastructure - Complete Summary

## What Was Created

### 1. Test Scripts

#### `test_mcp_client.py` - Full MCP Client Test
- **Purpose**: Automated testing script that mimics a real MCP client
- **Features**:
  - Establishes SSE connection like Forest Admin does
  - Performs initialize handshake
  - Runs multiple consecutive tool calls (configurable count)
  - Tracks success/failure patterns
  - Detects "every other" failure patterns
  - Measures timing and performance
  - Generates detailed reports

**Usage**:
```bash
# Test against Heroku (20 calls)
python test_mcp_client.py https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/mcp 20

# Test locally
python test_mcp_client.py http://localhost:8000/mcp 10
```

#### `test_simple.py` - Quick Connection Test
- **Purpose**: Quick health check and connectivity test
- **Features**:
  - Tests `/health` endpoint
  - Tests `/metrics` endpoint
  - Tests basic SSE connection
  - Simple pass/fail output

**Usage**:
```bash
python test_simple.py https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com
```

### 2. Enhanced Server Logging

#### Changes to `http_server.py`:
- ✅ Added comprehensive logging with timestamps
- ✅ Track all tool calls with unique IDs
- ✅ Log session lifecycle (connection/disconnection)
- ✅ Track request count and error count globally
- ✅ Log timing for each operation
- ✅ Log detailed error information with stack traces

**Example log output**:
```
2025-10-24 09:15:30 - [session_1] New SSE connection established
2025-10-24 09:15:31 - [session_1] Server.run() starting
2025-10-24 09:15:32 - [call_1] Tool call started: extract-pdf-contents
2025-10-24 09:15:32 - [call_1] Arguments: {'pdf_path': 'https://example.com/file.pdf', 'pages': '1'}
2025-10-24 09:15:32 - [call_1] Extracting from: https://example.com/file.pdf, pages: 1
2025-10-24 09:15:35 - [call_1] ✓ Extraction successful: 1250 chars in 3.15s
2025-10-24 09:15:40 - [session_1] SSE connection closed after 10.25s
```

#### Changes to `pdf_extractor.py`:
- ✅ Log file downloads (start, progress, completion)
- ✅ Log OCR operations with timing
- ✅ Log PDF type detection (scanned vs text-based)
- ✅ Log page selection and processing
- ✅ Log temp file creation and cleanup
- ✅ Detailed error logging with context

**Example log output**:
```
2025-10-24 09:15:32 - Starting content extraction: https://example.com/file.pdf, pages=1
2025-10-24 09:15:32 - Detected URL, downloading...
2025-10-24 09:15:32 - Downloading file from URL: https://example.com/file.pdf
2025-10-24 09:15:33 - Temp file created: /tmp/tmpxyz123.pdf
2025-10-24 09:15:33 - ✓ Downloaded 45678 bytes to /tmp/tmpxyz123.pdf
2025-10-24 09:15:33 - Processing file: /tmp/tmpxyz123.pdf (45678 bytes)
2025-10-24 09:15:33 - Processing as PDF file
2025-10-24 09:15:34 - PDF type: text-based
2025-10-24 09:15:34 - Total pages: 5, selected: 1
2025-10-24 09:15:34 - Using text extraction for normal PDF
2025-10-24 09:15:35 - ✓ Extraction complete: 1250 characters
2025-10-24 09:15:35 - Cleaning up temp file: /tmp/tmpxyz123.pdf
2025-10-24 09:15:35 - ✓ Temp file cleaned up
```

### 3. Health Check and Metrics Endpoints

#### `/health` Endpoint
Returns basic server health status:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-24T09:15:30.123Z",
  "active_sessions": 3,
  "total_requests": 127,
  "total_errors": 2
}
```

#### `/metrics` Endpoint
Returns detailed server metrics:
```json
{
  "server": {
    "name": "pdf_extraction",
    "version": "0.1.0",
    "uptime_seconds": 3600.5,
    "start_time": "2025-10-24T08:15:30.123Z"
  },
  "sessions": {
    "active": 3,
    "details": {
      "session_1": {
        "duration_seconds": 15.3,
        "requests": 5
      },
      "session_2": {
        "duration_seconds": 8.7,
        "requests": 2
      }
    }
  },
  "requests": {
    "total": 127,
    "errors": 2,
    "success_rate": "98.4%"
  },
  "resources": {
    "memory_rss_mb": 145.3,
    "memory_vms_mb": 312.8,
    "cpu_percent": 23.5,
    "threads": 8
  }
}
```

### 4. Documentation

#### `TESTING.md` - Complete Testing Guide
- How to install and run tests
- How to interpret test results
- Common failure patterns and their meanings
- How to monitor Heroku logs
- Troubleshooting guide
- Advanced debugging techniques

## Next Steps - What You Need to Do

### 1. Deploy the Updated Server

The new code with logging and metrics endpoints needs to be deployed to Heroku:

```bash
# Stage the changes
git add src/pdf_extraction/http_server.py
git add src/pdf_extraction/pdf_extractor.py
git add requirements.txt
git add test_mcp_client.py
git add test_simple.py
git add TESTING.md
git add TESTING_SUMMARY.md

# Commit
git commit -m "Add comprehensive logging, health/metrics endpoints, and test infrastructure

- Enhanced logging in http_server.py and pdf_extractor.py
- Added /health and /metrics endpoints for monitoring
- Created test_mcp_client.py for automated testing
- Created test_simple.py for quick health checks
- Added comprehensive testing documentation
- Track sessions, requests, errors globally
- Log detailed timing and operation info"

# Push to trigger Heroku deployment
git push origin master
```

### 2. Wait for Deployment

Watch the deployment:
```bash
heroku logs --tail --app pdf-extraction-mcp-54041c60e7d7
```

Wait for log messages like:
```
heroku[web.1]: State changed from starting to up
```

### 3. Verify Deployment

Test the new endpoints:
```bash
# Health check
curl https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/health

# Metrics
curl https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/metrics
```

### 4. Run the Tests

#### Install test dependencies:
```bash
pip install httpx httpx-sse psutil
```

#### Run full test suite:
```bash
python test_mcp_client.py https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/mcp 20
```

This will run 20 consecutive tool calls and report:
- ✓ Success count
- ✗ Failure count
- ⚠️ Failure patterns (e.g., "every other request fails")
- Timing statistics
- Detailed per-request results

### 5. Monitor While Testing

In another terminal, watch the logs:
```bash
heroku logs --tail --app pdf-extraction-mcp-54041c60e7d7
```

You'll see detailed logs like:
```
app[web.1]: [session_xyz] New SSE connection established
app[web.1]: [call_1] Tool call started: extract-pdf-contents
app[web.1]: [call_1] Extracting from: https://...
app[web.1]: [call_1] ✓ Extraction successful: 1250 chars in 3.15s
```

### 6. Check Metrics During Testing

While tests are running:
```bash
curl https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/metrics
```

Watch for:
- **Memory usage** (should stay < 300 MB)
- **CPU usage** (spikes during extraction are normal)
- **Error count** (should be 0 or very low)
- **Success rate** (should be > 98%)

### 7. Compare with Forest Admin

After running the automated tests:

**If automated tests succeed (100% success rate):**
- ✅ Server is working correctly
- ❌ Problem is with Forest Admin client
- → Check Forest Admin's session management
- → Check if Forest Admin is sending requests too quickly
- → Report to Forest Admin support with test results

**If automated tests fail with same "every other" pattern:**
- ❌ Server issue confirmed
- Look at Heroku logs for specific errors:
  - Temp file issues?
  - Memory issues?
  - Session state issues?
  - Race conditions?

### 8. Analyze the Pattern

If failures occur, look for patterns in the logs:

**Pattern: Every other request fails**
```
[call_1] ✓ Extraction successful
[call_2] ✗ Tool call failed
[call_3] ✓ Extraction successful
[call_4] ✗ Tool call failed
```
→ Likely: Session state or temp file cleanup issue

**Pattern: Random failures**
```
[call_1] ✓ Extraction successful
[call_2] ✓ Extraction successful
[call_3] ✗ Tool call failed
[call_4] ✓ Extraction successful
[call_5] ✓ Extraction successful
[call_6] ✗ Tool call failed
```
→ Likely: Resource exhaustion or network timeouts

**Pattern: First fails, rest succeed**
```
[call_1] ✗ Tool call failed
[call_2] ✓ Extraction successful
[call_3] ✓ Extraction successful
```
→ Likely: Cold start or initialization issue

## What to Share

When you run the tests, please share:

1. **Test output** from `test_mcp_client.py`
2. **Heroku logs** during the test period
3. **Metrics snapshot** from `/metrics` endpoint
4. **Forest Admin behavior** comparison

This will definitively tell us whether the issue is:
- ✅ Server-side (we can fix it)
- ✅ Forest Admin-side (they need to fix it)
- ✅ Infrastructure-side (upgrade Heroku dyno)

## Files Modified

- ✅ `src/pdf_extraction/http_server.py` - Added logging, health/metrics endpoints
- ✅ `src/pdf_extraction/pdf_extractor.py` - Added detailed logging
- ✅ `requirements.txt` - Added psutil
- ✅ `test_mcp_client.py` - New test script
- ✅ `test_simple.py` - New simple test script
- ✅ `TESTING.md` - Comprehensive testing guide
- ✅ `TESTING_SUMMARY.md` - This file
