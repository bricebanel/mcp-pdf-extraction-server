# PDF Extraction MCP server

MCP server to extract contents from a PDF file

## Components

### Tools

The server implements one tool:
- extract-pdf-contents: Extract contents from a local PDF file
  - Takes "pdf_path" as a required string argument, representing the local file path of the PDF file
  - Takes "pages" as an optional string argument, representing the page numbers to extract contents from the PDF file. Page numbers are separated in comma, and negative page numbers supported (e.g. '-1' means the last page)
  - Supports PDF file reader and OCR

## Quickstart

### Install

#### Claude Desktop

On MacOS: `~/Library/Application\ Support/Claude/claude_desktop_config.json`
On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

<details>
  <summary>Development/Unpublished Servers Configuration</summary>
  ```
  "mcpServers": {
    "pdf_extraction": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/xraywu/Workspace/pdf_extraction",
        "run",
        "pdf_extraction"
      ]
    }
  }
  ```
</details>

<details>
  <summary>Published Servers Configuration</summary>
  ```
  "mcpServers": {
    "pdf_extraction": {
      "command": "uvx",
      "args": [
        "pdf_extraction"
      ]
    }
  }
  ```
</details>