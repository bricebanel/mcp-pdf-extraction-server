from setuptools import setup, find_packages

setup(
    name="pdf-extraction",
    version="0.1.0",
    description="MCP server to extract contents from PDF files and images",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.11",
    install_requires=[
        "mcp>=1.2.0",
        "pypdf2>=3.0.1",
        "pytesseract>=0.3.10",
        "Pillow>=10.0.0",
        "pydantic>=2.10.1,<3.0.0",
        "pymupdf>=1.24.0",
        "uvicorn>=0.31.1",
        "starlette>=0.27",
    ],
    entry_points={
        "console_scripts": [
            "pdf-extraction=pdf_extraction:main",
            "pdf-extraction-http=pdf_extraction.http_server:main",
        ],
    },
)
