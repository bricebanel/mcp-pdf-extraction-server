# Upgrade to Streamable HTTP Transport (Modern MCP)

## What Changed

Alban was correct! The `/mcp` endpoint should use the modern **Streamable HTTP** transport, not the deprecated SSE transport.

### Before (Old SSE Transport)
```python
from mcp.server.sse import SseServerTransport
sse = SseServerTransport("/messages/")
# Complex routing with SSE and messages endpoints
```

### After (Modern Streamable HTTP)
```python
from mcp.server.streamable_http import create_streamable_http_app

app = create_streamable_http_app(
    server,
    path="/mcp",
    server_name="pdf_extraction",
    server_version="0.1.0"
)
```

## Why This Matters

1. **SSE is deprecated** - As of MCP spec 2025-03-26, SSE transport is the old way
2. **Streamable HTTP is modern** - Introduced in MCP SDK v1.8.0 (May 2025)
3. **Forest Admin uses Streamable HTTP** - That's why you were getting 405 errors
4. **Single endpoint** - Much simpler routing, just `/mcp` handles everything

## Benefits

- ✅ Works with Forest Admin's modern MCP client
- ✅ Bidirectional streaming over single HTTP connection
- ✅ Simpler code - no manual SSE/messages routing
- ✅ Future-proof for production deployments
- ✅ Supports both GET and POST to `/mcp`

## Deploy

```bash
cd /Users/bricebanel/Documents/mcp-pdf-extraction-server
git add src/pdf_extraction/http_server.py STREAMABLE_HTTP_UPGRADE.md
git commit -m "Upgrade to Streamable HTTP transport (modern MCP protocol)"
git push origin main
```

## Configuration

Use this URL in Forest Admin:
```
https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/mcp
```

The `/mcp` endpoint now:
- Accepts GET requests (for connection)
- Accepts POST requests (for messages)
- Handles streaming bidirectionally
- Works with modern MCP clients like Forest Admin

## Testing

After deployment, test with curl:
```bash
# Should return MCP protocol info
curl -X POST https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

You should get a proper JSON-RPC response, not a 405 error!
