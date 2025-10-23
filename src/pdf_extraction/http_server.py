from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import Response
from starlette.middleware.cors import CORSMiddleware
from .pdf_extractor import PDFExtractor
import uvicorn
import argparse


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


# Create SSE transport
sse = SseServerTransport("/messages")


async def handle_sse(request):
    """Handle SSE connection - creates a new server session for each SSE connection"""
    async with sse.connect_sse(
        request.scope,
        request.receive,
        request._send
    ) as streams:
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
    return Response()


# Create Starlette app
app = Starlette(
    routes=[
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
