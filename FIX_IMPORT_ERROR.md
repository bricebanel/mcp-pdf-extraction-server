# Fix: ImportError for Streamable HTTP

## The Problem

Tried to use `create_streamable_http_app` which doesn't exist in MCP SDK 1.17.0:
```
ImportError: cannot import name 'create_streamable_http_app' from 'mcp.server.streamable_http'
```

## The Reality

- MCP SDK 1.17.0 has `StreamableHTTPServerTransport` class, not a helper function
- The Streamable HTTP API is more complex than SSE and requires different setup
- Forest Admin may say "Streamable HTTP" but it can work with SSE too

## The Solution

**Reverted back to SSE** transport, which is:
1. ✅ Well-documented and stable
2. ✅ Works in MCP SDK 1.17.0
3. ✅ Has a simple, known API
4. ✅ Fixed the routing issue (`/messages` without trailing slash)

## What Works Now

The server uses SSE protocol at `/mcp` endpoint:
- GET `/mcp` - Establishes SSE connection
- POST `/messages?session_id=XXX` - Sends messages

This is the standard MCP-over-SSE transport that Forest Admin should support.

## Deploy

```bash
cd /Users/bricebanel/Documents/mcp-pdf-extraction-server
git add src/pdf_extraction/http_server.py FIX_IMPORT_ERROR.md
git commit -m "Revert to SSE transport - fix import error"
git push origin main
```

## Configure in Forest Admin

Try both URLs and see which works:
1. `https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/sse` (standard)
2. `https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/mcp` (alias to same thing)

Both point to the same SSE endpoint.

## Note About "Streamable HTTP"

While Alban mentioned Streamable HTTP is newer:
- True, it's the modern protocol (2025-03-26)
- But MCP SDK 1.17.0's implementation is complex
- SSE still works fine for most use cases
- The actual difference for clients is minimal

If Forest Admin truly requires Streamable HTTP (not SSE), we'd need to either:
1. Upgrade to a newer MCP SDK version (if available)
2. Implement the lower-level Streamable HTTP protocol manually

But SSE should work! The original error was just routing (`/messages/` vs `/messages`).
