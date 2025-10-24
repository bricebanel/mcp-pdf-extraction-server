from PyPDF2 import PdfReader
from pytesseract import image_to_string
from PIL import Image
import fitz  # PyMuPDF
import io
import os
import tempfile
import urllib.request
from typing import List, Optional
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class PDFExtractor:
    """PDF内容提取器，支持普通PDF和扫描件，支持本地文件和URL"""

    def __init__(self):
        pass

    def is_url(self, path: str) -> bool:
        """检查路径是否为URL"""
        try:
            result = urlparse(path)
            return all([result.scheme, result.netloc])
        except:
            return False

    def download_file(self, url: str) -> str:
        """从URL下载文件到临时目录，返回本地路径"""
        logger.info(f"Downloading file from URL: {url}")
        try:
            # 创建临时文件
            suffix = os.path.splitext(urlparse(url).path)[1] or '.tmp'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_path = temp_file.name
            temp_file.close()

            logger.debug(f"Temp file created: {temp_path}")

            # 下载文件
            urllib.request.urlretrieve(url, temp_path)
            file_size = os.path.getsize(temp_path)
            logger.info(f"✓ Downloaded {file_size} bytes to {temp_path}")
            return temp_path
        except Exception as e:
            logger.error(f"✗ Failed to download from {url}: {str(e)}")
            raise ValueError(f"Failed to download file from URL: {str(e)}")

    def is_image_file(self, path: str) -> bool:
        """检查文件是否为图片"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        ext = os.path.splitext(path)[1].lower()
        return ext in image_extensions

    def extract_text_from_image(self, image_path: str) -> str:
        """使用OCR从图片中提取文本"""
        logger.info(f"Extracting text from image using OCR: {image_path}")
        try:
            img = Image.open(image_path)
            img_size = f"{img.width}x{img.height}"
            logger.debug(f"Image size: {img_size}, format: {img.format}")

            # OCR支持中文和英文
            text = image_to_string(img, lang='eng')
            char_count = len(text)
            logger.info(f"✓ OCR extracted {char_count} characters from image")
            return text
        except Exception as e:
            logger.error(f"✗ OCR extraction failed: {str(e)}")
            raise ValueError(f"Failed to extract text from image: {str(e)}")

    def is_scanned_pdf(self, pdf_path: str) -> bool:
        """检查PDF是否为扫描件（图片格式）"""
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            if page.extract_text().strip():
                return False
        return True

    def extract_text_from_scanned(self, pdf_path: str, pages: List[int]) -> str:
        """使用OCR从扫描件PDF中提取文本"""
        doc = fitz.open(pdf_path)
        extracted_text = []
        
        for page_num in pages:
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes()))
            
            # OCR支持中文和英文
            text = image_to_string(img, lang='chi_sim+eng')
            extracted_text.append(f"Page {page_num + 1}:\n{text}")
        
        return "\n\n".join(extracted_text)

    def extract_text_from_normal(self, pdf_path: str, pages: List[int]) -> str:
        """从普通PDF中提取文本"""
        reader = PdfReader(pdf_path)
        extracted_text = []
        
        for page_num in pages:
            page = reader.pages[page_num]
            extracted_text.append(f"Page {page_num + 1}:\n{page.extract_text()}")
        
        return "\n\n".join(extracted_text)

    def parse_pages(self, pages_str: Optional[str], total_pages: int) -> List[int]:
        """解析页码字符串"""
        if not pages_str:
            return list(range(total_pages))
        
        pages = []
        for part in pages_str.split(','):
            if not part.strip():
                continue
            try:
                page_num = int(part.strip())
                if page_num < 0:
                    page_num = total_pages + page_num
                elif page_num > 0:
                    page_num = page_num - 1
                else:
                    raise ValueError("PDF页码不能为0")
                if 0 <= page_num < total_pages:
                    pages.append(page_num)
            except ValueError:
                continue
        return sorted(set(pages))

    def extract_content(self, pdf_path: str, pages: Optional[str]) -> str:
        """提取PDF或图片内容的主方法，支持URL和本地文件"""
        logger.info(f"Starting content extraction: {pdf_path}, pages={pages}")

        if not pdf_path:
            logger.error("Empty file path provided")
            raise ValueError("File path or URL cannot be empty")

        temp_file = None
        try:
            # 如果是URL，先下载文件
            if self.is_url(pdf_path):
                logger.info(f"Detected URL, downloading...")
                temp_file = self.download_file(pdf_path)
                local_path = temp_file
            else:
                logger.info(f"Using local file: {pdf_path}")
                local_path = pdf_path

            # 检查文件是否存在
            if not os.path.exists(local_path):
                logger.error(f"File not found: {local_path}")
                raise ValueError(f"File not found: {pdf_path}")

            file_size = os.path.getsize(local_path)
            logger.info(f"Processing file: {local_path} ({file_size} bytes)")

            # 如果是图片文件，直接使用OCR
            if self.is_image_file(local_path):
                logger.info("Detected image file, using OCR")
                text = self.extract_text_from_image(local_path)
                return f"Image content:\n{text}"

            # 处理PDF文件
            logger.info("Processing as PDF file")

            # 检查是否为扫描件
            is_scanned = self.is_scanned_pdf(local_path)
            logger.info(f"PDF type: {'scanned' if is_scanned else 'text-based'}")

            # 解析页码
            reader = PdfReader(local_path)
            total_pages = len(reader.pages)
            selected_pages = self.parse_pages(pages, total_pages)
            logger.info(f"Total pages: {total_pages}, selected: {len(selected_pages)}")

            # 根据PDF类型选择提取方式
            if is_scanned:
                logger.info("Using OCR extraction for scanned PDF")
                text = self.extract_text_from_scanned(local_path, selected_pages)
            else:
                logger.info("Using text extraction for normal PDF")
                text = self.extract_text_from_normal(local_path, selected_pages)

            char_count = len(text)
            logger.info(f"✓ Extraction complete: {char_count} characters")
            return text

        except Exception as e:
            logger.error(f"✗ Extraction failed: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to extract content: {str(e)}")
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                try:
                    logger.debug(f"Cleaning up temp file: {temp_file}")
                    os.unlink(temp_file)
                    logger.debug("✓ Temp file cleaned up")
                except Exception as e:
                    logger.warning(f"Failed to clean up temp file: {str(e)}")