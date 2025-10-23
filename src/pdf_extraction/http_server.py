from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.streamable_http import StreamableHTTPServerTransport
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
from .pdf_extractor import PDFExtractor
import uvicorn
import argparse
import anyio


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
    if name == "extract-pdf-contents":
        if not arguments:
            raise ValueError("Missing arguments")

        pdf_path = arguments.get("pdf_path")
        pages = arguments.get("pages")

        if not pdf_path:
            raise ValueError("Missing file path")

        extractor = PDFExtractor()
        extracted_text = extractor.extract_content(pdf_path, pages)
        return [
            types.TextContent(
                type="text",
                text=extracted_text,
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")


# Create StreamableHTTP transport handler
async def handle_mcp(request):
    """Handle MCP StreamableHTTP requests"""
    # Create transport for this request
    transport = StreamableHTTPServerTransport(
        mcp_session_id=None,
        is_json_response_enabled=True
    )

    # Run server and handle request concurrently
    async with transport.connect() as streams:
        async def run_mcp_server():
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

        async with anyio.create_task_group() as tg:
            # Start the MCP server in the background
            tg.start_soon(run_mcp_server)
            # Handle the HTTP request in the foreground
            try:
                await transport.handle_request(
                    request.scope,
                    request.receive,
                    request._send
                )
            finally:
                # Cancel the server task when done
                tg.cancel_scope.cancel()


# Create Starlette app with CORS
app = Starlette(
    routes=[
        Route("/mcp", endpoint=handle_mcp, methods=["GET", "POST", "DELETE"]),
    ]
)

# Add CORS middleware for browser clients
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
    print(f"MCP Streamable HTTP endpoint: http://{args.host}:{args.port}/mcp")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
