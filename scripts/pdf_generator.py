#!/usr/bin/env python3
"""
PDF Generator Module

Creates enhanced PDF files with bionic reading transformation applied.
Reconstructs the original layout while applying text enhancements.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch, mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Frame, SimpleDocTemplate
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import os
import re

from pdf_extractor import PDFDocument, PageContent, TextBlock, ImageBlock, TableBlock
from bionic_reader import BionicReader, BionicConfig


# Font paths
FONT_PATHS = {
    'normal': '/usr/share/fonts/truetype/english/calibri-regular.ttf',
    'bold': '/usr/share/fonts/truetype/english/calibri-bold.ttf',
    'italic': '/usr/share/fonts/truetype/english/calibri-italic.ttf',
    'chinese': '/usr/share/fonts/truetype/chinese/SimHei.ttf',
    'chinese_bold': '/usr/share/fonts/truetype/chinese/SimHei.ttf',
    'times': '/usr/share/fonts/truetype/english/Times-New-Roman.ttf',
}


class FontManager:
    """Manage font registration and selection."""

    def __init__(self):
        self.registered_fonts = {}
        self._register_fonts()

    def _register_fonts(self):
        """Register all available fonts."""
        # Register normal font
        if os.path.exists(FONT_PATHS.get('normal', '')):
            try:
                pdfmetrics.registerFont(TTFont('BionicNormal', FONT_PATHS['normal']))
                self.registered_fonts['normal'] = 'BionicNormal'
                print("Registered font: BionicNormal (for regular text)")
            except Exception as e:
                print(f"Warning: Could not register normal font: {e}")

        # Register bold font
        if os.path.exists(FONT_PATHS.get('bold', '')):
            try:
                pdfmetrics.registerFont(TTFont('BionicBold', FONT_PATHS['bold']))
                self.registered_fonts['bold'] = 'BionicBold'
                print("Registered font: BionicBold (for emphasized text)")
            except Exception as e:
                print(f"Warning: Could not register bold font: {e}")

        # Register Chinese font
        if os.path.exists(FONT_PATHS.get('chinese', '')):
            try:
                pdfmetrics.registerFont(TTFont('BionicChinese', FONT_PATHS['chinese']))
                self.registered_fonts['chinese'] = 'BionicChinese'
                print("Registered font: BionicChinese (for CJK text)")
            except Exception as e:
                print(f"Warning: Could not register Chinese font: {e}")

        # Fallback to Helvetica if no fonts available
        if 'normal' not in self.registered_fonts:
            self.registered_fonts['normal'] = 'Helvetica'
            self.registered_fonts['bold'] = 'Helvetica-Bold'
            print("Using fallback: Helvetica")

    def get_font(self, is_bold: bool = False, is_cjk: bool = False) -> str:
        """Get appropriate font name."""
        if is_cjk and 'chinese' in self.registered_fonts:
            return self.registered_fonts['chinese']
        if is_bold and 'bold' in self.registered_fonts:
            return self.registered_fonts['bold']
        return self.registered_fonts.get('normal', 'Helvetica')


@dataclass
class GeneratorConfig:
    """Configuration for PDF generation."""
    output_path: str
    apply_bionic: bool = True
    bionic_config: Optional[BionicConfig] = None
    preserve_layout: bool = True
    page_size: Tuple[float, float] = None
    margin: float = 0.5 * inch
    add_page_numbers: bool = True
    accessibility_tags: bool = True


class PDFGenerator:
    """Generate PDF files with bionic reading enhancements."""

    def __init__(self, config: GeneratorConfig):
        """Initialize the generator with configuration."""
        self.config = config
        self.font_manager = FontManager()
        self.bionic_reader = BionicReader(config.bionic_config or BionicConfig())

    def detect_cjk(self, text: str) -> bool:
        """Detect if text contains CJK characters."""
        for char in text:
            code = ord(char)
            if 0x4E00 <= code <= 0x9FFF:
                return True
        return False

    def parse_bionic_text(self, text: str) -> List[Tuple[str, bool]]:
        """
        Parse text with **bold** markers into segments.
        Returns list of (text, is_bold) tuples.
        """
        segments = []
        pattern = r'\*\*(.+?)\*\*'

        last_end = 0
        for match in re.finditer(pattern, text):
            # Text before bold
            if match.start() > last_end:
                segments.append((text[last_end:match.start()], False))
            # Bold text
            segments.append((match.group(1), True))
            last_end = match.end()

        # Remaining text
        if last_end < len(text):
            segments.append((text[last_end:], False))

        return segments if segments else [(text, False)]

    def transform_text_block(self, block: TextBlock) -> str:
        """Transform a text block with bionic reading."""
        if self.config.apply_bionic:
            return self.bionic_reader.transform(block.text)
        return block.text

    def draw_text_block(self, canvas_obj, block: TextBlock, page_height: float):
        """Draw a text block on the canvas with bionic enhancement."""
        text = self.transform_text_block(block)
        segments = self.parse_bionic_text(text)

        font_size = block.font_size or 12
        is_cjk = self.detect_cjk(text)

        # PDF coordinates: (0,0) is bottom-left
        x = block.x0
        y = page_height - block.y0 - font_size * 0.8

        # Draw each segment with appropriate font
        current_x = x

        for segment_text, is_bold in segments:
            if not segment_text:
                continue

            # Get the right font
            font_name = self.font_manager.get_font(is_bold=is_bold, is_cjk=is_cjk)

            # Set the font
            canvas_obj.setFont(font_name, font_size)

            # Draw the text
            canvas_obj.drawString(current_x, y, segment_text)

            # Calculate width for next position
            text_width = canvas_obj.stringWidth(segment_text, font_name, font_size)
            current_x += text_width

    def draw_page_number(self, canvas_obj, page_num: int, total_pages: int, page_width: float, page_height: float):
        """Draw page number at bottom center."""
        if not self.config.add_page_numbers:
            return

        text = f"Page {page_num} of {total_pages}"
        canvas_obj.setFont('Helvetica', 10)
        text_width = canvas_obj.stringWidth(text, 'Helvetica', 10)
        x = (page_width - text_width) / 2
        y = 30

        canvas_obj.drawString(x, y, text)

    def generate_simple_pdf(self, document: PDFDocument) -> str:
        """Generate a simple PDF with text content preserving layout."""
        output_path = self.config.output_path

        # Create canvas with first page dimensions
        if document.pages:
            page_width = document.pages[0].width
            page_height = document.pages[0].height
        else:
            page_width, page_height = letter

        c = canvas.Canvas(output_path, pagesize=(page_width, page_height))

        for i, page in enumerate(document.pages):
            # Set page size for this page
            c.setPageSize((page.width, page.height))

            # Draw text blocks with bionic enhancement
            for block in page.text_blocks:
                self.draw_text_block(c, block, page.height)

            # Draw page number
            self.draw_page_number(c, i + 1, document.num_pages, page.width, page.height)

            # Create new page
            c.showPage()

        c.save()
        return output_path

    def generate_text_flow_pdf(self, document: PDFDocument) -> str:
        """Generate a PDF with flowing text (better for reading)."""
        output_path = self.config.output_path

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Create styles with our registered fonts
        normal_font = self.font_manager.get_font(is_bold=False)
        bold_font = self.font_manager.get_font(is_bold=True)

        styles = getSampleStyleSheet()

        # Custom styles for bionic reading
        normal_style = ParagraphStyle(
            'BionicNormal',
            parent=styles['Normal'],
            fontName=normal_font,
            fontSize=12,
            leading=16,
            spaceAfter=12,
            alignment=TA_JUSTIFY
        )

        heading_style = ParagraphStyle(
            'BionicHeading',
            parent=styles['Heading1'],
            fontName=bold_font,
            fontSize=16,
            leading=20,
            spaceAfter=20,
            spaceBefore=20
        )

        # Build content
        story = []

        for page in document.pages:
            # Group text blocks into paragraphs
            paragraphs = self._group_into_paragraphs(page.text_blocks)

            for para_blocks in paragraphs:
                # Combine text
                text = ' '.join(block.text for block in para_blocks)

                # Apply bionic transformation
                if self.config.apply_bionic:
                    text = self.bionic_reader.transform(text)

                # Convert **text** to <b>text</b> for ReportLab
                text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

                # Determine if heading based on font size
                is_heading = any(
                    block.font_size and block.font_size > 14
                    for block in para_blocks
                )

                style = heading_style if is_heading else normal_style

                try:
                    para = Paragraph(text, style)
                    story.append(para)
                except Exception as e:
                    print(f"Warning: Could not create paragraph: {e}")
                    # Fallback
                    safe_text = text.replace('<', '&lt;').replace('>', '&gt;')
                    story.append(Paragraph(safe_text, style))

        doc.build(story)
        return output_path

    def _group_into_paragraphs(self, blocks: List[TextBlock], y_tolerance: float = 5) -> List[List[TextBlock]]:
        """Group text blocks into paragraphs based on position."""
        if not blocks:
            return []

        sorted_blocks = sorted(blocks, key=lambda b: (b.y0, b.x0))

        paragraphs = []
        current_para = [sorted_blocks[0]]
        last_y = sorted_blocks[0].y0
        last_font_size = sorted_blocks[0].font_size or 12

        for block in sorted_blocks[1:]:
            y_diff = abs(block.y0 - last_y)
            font_size = block.font_size or 12

            if y_diff < last_font_size * 0.3:
                current_para.append(block)
            elif y_diff > last_font_size * 1.5:
                paragraphs.append(current_para)
                current_para = [block]
            else:
                current_para.append(block)

            last_y = block.y0
            last_font_size = font_size

        if current_para:
            paragraphs.append(current_para)

        return paragraphs


def generate_bionic_pdf(
    document: PDFDocument,
    output_path: str,
    bionic_config: Optional[BionicConfig] = None,
    preserve_layout: bool = True
) -> str:
    """Convenience function to generate a bionic PDF."""
    config = GeneratorConfig(
        output_path=output_path,
        apply_bionic=True,
        bionic_config=bionic_config,
        preserve_layout=preserve_layout
    )

    generator = PDFGenerator(config)

    if preserve_layout:
        return generator.generate_simple_pdf(document)
    else:
        return generator.generate_text_flow_pdf(document)


def main():
    """Command-line interface for PDF generation."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Generate enhanced PDF with bionic reading")
    parser.add_argument("input", help="Input JSON file from pdf_extractor")
    parser.add_argument("-o", "--output", required=True, help="Output PDF file path")
    parser.add_argument("-r", "--ratio", type=float, default=0.4, help="Emphasis ratio (0.1-0.7)")
    parser.add_argument("-i", "--intensity", choices=["light", "medium", "heavy"], default="medium")
    parser.add_argument("--no-bionic", action="store_true", help="Disable bionic transformation")
    parser.add_argument("--flow", action="store_true", help="Use flowing text layout")

    args = parser.parse_args()

    # Load document from JSON
    with open(args.input, 'r', encoding='utf-8') as f:
        doc_data = json.load(f)

    # Reconstruct document object
    document = PDFDocument(
        filename=doc_data['filename'],
        num_pages=doc_data['num_pages'],
        metadata=doc_data.get('metadata', {}),
        pages=[]
    )

    for page_data in doc_data['pages']:
        page = PageContent(
            page_num=page_data['page_num'],
            width=page_data['width'],
            height=page_data['height'],
            text_blocks=[],
            image_blocks=[],
            table_blocks=[]
        )

        for block_data in page_data['text_blocks']:
            block = TextBlock(
                text=block_data['text'],
                x0=block_data['x0'],
                y0=block_data['y0'],
                x1=block_data['x1'],
                y1=block_data['y1'],
                page_num=block_data['page_num'],
                font_name=block_data.get('font_name'),
                font_size=block_data.get('font_size'),
                is_bold=block_data.get('is_bold', False),
                is_italic=block_data.get('is_italic', False)
            )
            page.text_blocks.append(block)

        document.pages.append(page)

    # Create bionic config
    bionic_config = BionicConfig(
        emphasis_ratio=args.ratio,
        bold_intensity=args.intensity
    )

    # Generate PDF
    config = GeneratorConfig(
        output_path=args.output,
        apply_bionic=not args.no_bionic,
        bionic_config=bionic_config,
        preserve_layout=not args.flow
    )

    generator = PDFGenerator(config)

    if args.flow:
        output = generator.generate_text_flow_pdf(document)
    else:
        output = generator.generate_simple_pdf(document)

    print(f"Generated PDF: {output}")


if __name__ == "__main__":
    main()
