from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from .pdf_extractor import PDFExtractor


# MCP 服务器配置
server = Server("pdf_extraction")

# MCP 工具配置
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Tools for PDF contents extraction
    """
    return [
        types.Tool(
            name="extract-pdf-contents",
            description="Extract contents from a local PDF file, given page numbers separated in comma. Negative page index number supported.",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {"type": "string"},
                    "pages": {"type": "string"},
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


# 启动主函数
async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="pdf_extraction",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )