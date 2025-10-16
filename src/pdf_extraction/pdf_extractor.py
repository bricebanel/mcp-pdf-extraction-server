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
        try:
            # 创建临时文件
            suffix = os.path.splitext(urlparse(url).path)[1] or '.tmp'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_path = temp_file.name
            temp_file.close()

            # 下载文件
            urllib.request.urlretrieve(url, temp_path)
            return temp_path
        except Exception as e:
            raise ValueError(f"Failed to download file from URL: {str(e)}")

    def is_image_file(self, path: str) -> bool:
        """检查文件是否为图片"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        ext = os.path.splitext(path)[1].lower()
        return ext in image_extensions

    def extract_text_from_image(self, image_path: str) -> str:
        """使用OCR从图片中提取文本"""
        try:
            img = Image.open(image_path)
            # OCR支持中文和英文
            text = image_to_string(img, lang='eng')
            return text
        except Exception as e:
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
        if not pdf_path:
            raise ValueError("File path or URL cannot be empty")

        temp_file = None
        try:
            # 如果是URL，先下载文件
            if self.is_url(pdf_path):
                temp_file = self.download_file(pdf_path)
                local_path = temp_file
            else:
                local_path = pdf_path

            # 检查文件是否存在
            if not os.path.exists(local_path):
                raise ValueError(f"File not found: {pdf_path}")

            # 如果是图片文件，直接使用OCR
            if self.is_image_file(local_path):
                text = self.extract_text_from_image(local_path)
                return f"Image content:\n{text}"

            # 处理PDF文件
            # 检查是否为扫描件
            is_scanned = self.is_scanned_pdf(local_path)

            # 解析页码
            reader = PdfReader(local_path)
            total_pages = len(reader.pages)
            selected_pages = self.parse_pages(pages, total_pages)

            # 根据PDF类型选择提取方式
            if is_scanned:
                text = self.extract_text_from_scanned(local_path, selected_pages)
            else:
                text = self.extract_text_from_normal(local_path, selected_pages)

            return text
        except Exception as e:
            raise ValueError(f"Failed to extract content: {str(e)}")
        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass