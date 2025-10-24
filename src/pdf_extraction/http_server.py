from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import Response, JSONResponse
from starlette.middleware.cors import CORSMiddleware
from .pdf_extractor import PDFExtractor
import uvicorn
import argparse
import logging
import time
from datetime import datetime


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Track active sessions and metrics
active_sessions = {}
request_count = 0
error_count = 0
start_time = datetime.now()

# Forest Admin workaround metrics
zombie_sessions_cleaned = 0
uninitialized_session_errors = 0
initialization_timeout_seconds = 30  # Close sessions that don't initialize within 30s

# MCP Server configuration
server = Server("pdf_extraction")

# MCP tool configuration
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Tools for PDF contents extraction
    """
    return [
        types.Tool(
            name="extract-pdf-contents",
            description="Extract contents from a PDF file or image (PNG, JPG, etc). Supports both local file paths and URLs. For PDFs, you can specify page numbers separated by commas. Negative page index numbers are supported (e.g., -1 for the last page). For images, OCR will be used to extract text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Local file path or URL to the PDF or image file"
                    },
                    "pages": {
                        "type": "string",
                        "description": "Optional: Comma-separated page numbers for PDFs (e.g., '1,2,3' or '1,-1'). Omit for images or to extract all pages."
                    },
                },
                "required": ["pdf_path"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Tools for PDF content extraction
    """
    global request_count, error_count
    request_count += 1

    call_id = f"call_{request_count}"
    start_time_call = time.time()

    logger.info(f"[{call_id}] Tool call started: {name}")
    logger.info(f"[{call_id}] Arguments: {arguments}")

    try:
        if name == "extract-pdf-contents":
            if not arguments:
                error_count += 1
                logger.error(f"[{call_id}] Missing arguments")
                raise ValueError("Missing arguments")

            pdf_path = arguments.get("pdf_path")
            pages = arguments.get("pages")

            if not pdf_path:
                error_count += 1
                logger.error(f"[{call_id}] Missing file path")
                raise ValueError("Missing file path")

            logger.info(f"[{call_id}] Extracting from: {pdf_path}, pages: {pages}")

            extractor = PDFExtractor()
            extracted_text = extractor.extract_content(pdf_path, pages)

            duration = time.time() - start_time_call
            content_length = len(extracted_text)

            logger.info(f"[{call_id}] ✓ Extraction successful: {content_length} chars in {duration:.2f}s")

            return [
                types.TextContent(
                    type="text",
                    text=extracted_text,
                )
            ]
        else:
            error_count += 1
            logger.error(f"[{call_id}] Unknown tool: {name}")
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error_count += 1
        duration = time.time() - start_time_call
        logger.error(f"[{call_id}] ✗ Tool call failed after {duration:.2f}s: {str(e)}", exc_info=True)
        raise


# Create SSE transport
sse = SseServerTransport("/messages")

# Wrap the message handler to track session initialization
_original_handle_post_message = sse.handle_post_message

async def _tracked_handle_post_message(scope, receive, send):
    """Wrapper to track session initialization and requests"""
    # Extract session ID from query params
    query_string = scope.get("query_string", b"").decode()
    if "session_id=" in query_string:
        session_id = query_string.split("session_id=")[1].split("&")[0]

        # Update session tracking
        if session_id in active_sessions:
            if not active_sessions[session_id]["initialized"]:
                active_sessions[session_id]["initialized"] = True
                logger.info(f"[{session_id}] Session marked as initialized (first request received)")

            active_sessions[session_id]["requests"] += 1

    # Call original handler
    return await _original_handle_post_message(scope, receive, send)

# Replace the handler
sse.handle_post_message = _tracked_handle_post_message


async def handle_sse(request):
    """Handle SSE connection - creates a new server session for each SSE connection"""
    session_id = request.query_params.get("session_id", f"session_{len(active_sessions)+1}")

    logger.info(f"[{session_id}] New SSE connection established")
    active_sessions[session_id] = {
        "start_time": datetime.now(),
        "requests": 0,
        "initialized": False,  # Track if session has been initialized
        "zombie_check_scheduled": False
    }

    try:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send
        ) as streams:
            logger.info(f"[{session_id}] Server.run() starting")

            await server.run(
                streams[0],
                streams[1],
                InitializationOptions(
                    server_name="pdf_extraction",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

            logger.info(f"[{session_id}] Server.run() completed normally")
    except Exception as e:
        logger.error(f"[{session_id}] SSE connection error: {str(e)}", exc_info=True)
    finally:
        if session_id in active_sessions:
            session_info = active_sessions[session_id]
            duration = (datetime.now() - session_info["start_time"]).total_seconds()
            was_initialized = session_info["initialized"]
            request_count = session_info["requests"]

            logger.info(
                f"[{session_id}] SSE connection closed after {duration:.2f}s "
                f"(initialized={was_initialized}, requests={request_count})"
            )

            # Track zombie sessions for monitoring
            if not was_initialized and duration > 10:
                global zombie_sessions_cleaned
                zombie_sessions_cleaned += 1
                logger.warning(
                    f"[{session_id}] ZOMBIE SESSION: Never initialized, open for {duration:.1f}s "
                    f"(likely Forest Admin bug)"
                )

            del active_sessions[session_id]

    return Response()


async def health_check(request):
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sessions": len(active_sessions),
        "total_requests": request_count,
        "total_errors": error_count
    })


async def metrics(request):
    """Metrics endpoint"""
    import psutil
    import os

    uptime = (datetime.now() - start_time).total_seconds()

    # Get process info
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    # Count uninitialized sessions (zombie sessions)
    zombie_sessions = sum(1 for s in active_sessions.values() if not s["initialized"])
    uninitialized_sessions_long_lived = sum(
        1 for s in active_sessions.values()
        if not s["initialized"] and (datetime.now() - s["start_time"]).total_seconds() > 10
    )

    # Check if Forest Admin bug is still present
    forest_admin_bug_detected = zombie_sessions > 0 or zombie_sessions_cleaned > 0

    return JSONResponse({
        "server": {
            "name": "pdf_extraction",
            "version": "0.1.0",
            "uptime_seconds": uptime,
            "start_time": start_time.isoformat()
        },
        "sessions": {
            "active": len(active_sessions),
            "uninitialized": zombie_sessions,
            "uninitialized_long_lived": uninitialized_sessions_long_lived,
            "details": {
                sid: {
                    "duration_seconds": (datetime.now() - info["start_time"]).total_seconds(),
                    "requests": info["requests"],
                    "initialized": info["initialized"]
                }
                for sid, info in active_sessions.items()
            }
        },
        "requests": {
            "total": request_count,
            "errors": error_count,
            "success_rate": f"{((request_count - error_count) / request_count * 100):.1f}%" if request_count > 0 else "N/A"
        },
        "forest_admin_workaround": {
            "enabled": True,
            "bug_detected": forest_admin_bug_detected,
            "zombie_sessions_cleaned_total": zombie_sessions_cleaned,
            "uninitialized_errors_total": uninitialized_session_errors,
            "status": "BUG_PRESENT" if zombie_sessions > 0 else ("BUG_FIXED" if zombie_sessions_cleaned == 0 else "WORKAROUND_ACTIVE"),
            "message": (
                "⚠️ Forest Admin is creating uninitialized sessions - workaround active"
                if zombie_sessions > 0
                else ("✅ No issues detected - Forest Admin may have fixed the bug!"
                      if zombie_sessions_cleaned == 0
                      else "✅ Workaround preventing zombie sessions")
            )
        },
        "resources": {
            "memory_rss_mb": memory_info.rss / 1024 / 1024,
            "memory_vms_mb": memory_info.vms / 1024 / 1024,
            "cpu_percent": process.cpu_percent(interval=0.1),
            "threads": process.num_threads()
        }
    })


# Create Starlette app
app = Starlette(
    routes=[
        Route("/health", endpoint=health_check, methods=["GET"]),
        Route("/metrics", endpoint=metrics, methods=["GET"]),
        Route("/mcp", endpoint=handle_sse, methods=["GET"]),
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/messages", app=sse.handle_post_message),
    ]
)

# Add CORS middleware for browser clients (though browsers won't work due to lack of SSE support)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


def main():
    """Run the HTTP server"""
    parser = argparse.ArgumentParser(description="PDF Extraction MCP HTTP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()

    print(f"Starting PDF Extraction MCP Server on http://{args.host}:{args.port}")
    print(f"MCP SSE endpoint: http://{args.host}:{args.port}/mcp")
    print(f"MCP SSE endpoint (alt): http://{args.host}:{args.port}/sse")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
