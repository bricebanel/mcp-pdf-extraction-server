from PyPDF2 import PdfReader
from pytesseract import image_to_string
from PIL import Image
import fitz  # PyMuPDF
import io
from typing import List, Optional


class PDFExtractor:
    """PDF内容提取器，支持普通PDF和扫描件"""
    
    def __init__(self):
        pass

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

    def extract_content(self, pdf_path: str, pages: Optional[str]) -> List[str]:
        """提取PDF内容的主方法"""
        if not pdf_path:
            raise ValueError("PDF路径不能为空")

        try:
            # 检查是否为扫描件
            is_scanned = self.is_scanned_pdf(pdf_path)
            
            # 解析页码
            reader = PdfReader(pdf_path)
            total_pages = len(reader.pages)
            selected_pages = self.parse_pages(pages, total_pages)
            
            # 根据PDF类型选择提取方式
            if is_scanned:
                text = self.extract_text_from_scanned(pdf_path, selected_pages)
            else:
                text = self.extract_text_from_normal(pdf_path, selected_pages)
                
            return text
        except Exception as e:
            raise ValueError(f"提取PDF内容失败: {str(e)}")