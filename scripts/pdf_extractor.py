#!/usr/bin/env python3
"""
PDF Extractor Module

Extracts text and structure from PDF files while preserving layout,
positioning, and formatting information for later reconstruction.
"""

import pdfplumber
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
import json
import os


@dataclass
class TextBlock:
    """Represents a text block with position and formatting information."""
    text: str
    x0: float  # Left coordinate
    y0: float  # Top coordinate
    x1: float  # Right coordinate
    y1: float  # Bottom coordinate
    page_num: int
    font_name: Optional[str] = None
    font_size: Optional[float] = None
    font_weight: Optional[str] = None  # 'normal', 'bold', etc.
    is_bold: bool = False
    is_italic: bool = False
    color: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def mid_y(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class ImageBlock:
    """Represents an image in the PDF."""
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int
    width: int
    height: int
    image_data: Optional[bytes] = None
    format: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary (without image data)."""
        return {
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "page_num": self.page_num,
            "width": self.width,
            "height": self.height,
            "format": self.format
        }


@dataclass
class TableBlock:
    """Represents a table in the PDF."""
    x0: float
    y0: float
    x1: float
    y1: float
    page_num: int
    rows: List[List[str]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "page_num": self.page_num,
            "rows": self.rows
        }


@dataclass
class PageContent:
    """Represents all content on a single page."""
    page_num: int
    width: float
    height: float
    text_blocks: List[TextBlock] = field(default_factory=list)
    image_blocks: List[ImageBlock] = field(default_factory=list)
    table_blocks: List[TableBlock] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "page_num": self.page_num,
            "width": self.width,
            "height": self.height,
            "text_blocks": [b.to_dict() for b in self.text_blocks],
            "image_blocks": [b.to_dict() for b in self.image_blocks],
            "table_blocks": [b.to_dict() for b in self.table_blocks]
        }


@dataclass
class PDFDocument:
    """Represents an entire PDF document."""
    filename: str
    num_pages: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    pages: List[PageContent] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "filename": self.filename,
            "num_pages": self.num_pages,
            "metadata": self.metadata,
            "pages": [p.to_dict() for p in self.pages]
        }

    def to_json(self, filepath: str) -> None:
        """Save document structure to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def get_all_text(self) -> str:
        """Get all text content as a single string."""
        texts = []
        for page in self.pages:
            for block in page.text_blocks:
                texts.append(block.text)
        return '\n'.join(texts)


class PDFExtractor:
    """Extract content from PDF files."""

    def __init__(self, extract_images: bool = True, extract_tables: bool = True):
        """Initialize the extractor."""
        self._should_extract_images = extract_images
        self._should_extract_tables = extract_tables

    def extract_font_info(self, char: Dict) -> Tuple[str, float, bool, bool]:
        """Extract font information from a character."""
        font_name = char.get('fontname', 'Unknown')
        font_size = char.get('size', 12)
        is_bold = False
        is_italic = False

        # Detect bold and italic from font name
        font_lower = font_name.lower() if font_name else ''
        is_bold = 'bold' in font_lower or 'black' in font_lower or 'heavy' in font_lower
        is_italic = 'italic' in font_lower or 'oblique' in font_lower

        # Check for common bold font prefixes
        if font_name:
            for prefix in ['Bold', 'Heavy', 'Black']:
                if prefix in font_name:
                    is_bold = True

        return font_name, font_size, is_bold, is_italic

    def extract_text_blocks(self, page, page_num: int) -> List[TextBlock]:
        """Extract text blocks from a page with formatting info."""
        blocks = []

        # Get characters with detailed info
        chars = page.chars
        if not chars:
            return blocks

        # Group characters by line (similar y-position)
        lines = {}
        y_tolerance = 2  # pixels

        for char in chars:
            y_key = round(char['top'] / y_tolerance) * y_tolerance
            if y_key not in lines:
                lines[y_key] = []
            lines[y_key].append(char)

        # Process each line
        for y_key in sorted(lines.keys(), reverse=True):  # Top to bottom
            line_chars = sorted(lines[y_key], key=lambda c: c['x0'])  # Left to right

            if not line_chars:
                continue

            # Group characters into words/blocks
            current_block = []
            current_font = None
            current_size = None
            current_bold = False
            current_italic = False
            block_start_x = line_chars[0]['x0']

            for i, char in enumerate(line_chars):
                font_name, font_size, is_bold, is_italic = self.extract_font_info(char)

                # Check if we should start a new block
                font_changed = (current_font != font_name or
                               current_size != font_size or
                               current_bold != is_bold or
                               current_italic != is_italic)

                # Check for horizontal gap
                if current_block and i > 0:
                    prev_char = line_chars[i-1]
                    gap = char['x0'] - prev_char['x1']
                    if gap > font_size * 0.5:  # Significant gap
                        font_changed = True

                if font_changed and current_block:
                    # Save current block
                    text = ''.join(c['text'] for c in current_block)
                    if text.strip():
                        block = TextBlock(
                            text=text,
                            x0=block_start_x,
                            y0=current_block[0]['top'],
                            x1=current_block[-1]['x1'],
                            y1=current_block[-1]['bottom'],
                            page_num=page_num,
                            font_name=current_font,
                            font_size=current_size,
                            is_bold=current_bold,
                            is_italic=current_italic
                        )
                        blocks.append(block)

                    # Start new block
                    current_block = [char]
                    block_start_x = char['x0']
                    current_font = font_name
                    current_size = font_size
                    current_bold = is_bold
                    current_italic = is_italic
                else:
                    current_block.append(char)
                    if not current_font:
                        current_font = font_name
                        current_size = font_size
                        current_bold = is_bold
                        current_italic = is_italic

            # Don't forget the last block in the line
            if current_block:
                text = ''.join(c['text'] for c in current_block)
                if text.strip():
                    block = TextBlock(
                        text=text,
                        x0=block_start_x,
                        y0=current_block[0]['top'],
                        x1=current_block[-1]['x1'],
                        y1=current_block[-1]['bottom'],
                        page_num=page_num,
                        font_name=current_font,
                        font_size=current_size,
                        is_bold=current_bold,
                        is_italic=current_italic
                    )
                    blocks.append(block)

        return blocks

    def extract_images_from_page(self, page, page_num: int) -> List[ImageBlock]:
        """Extract images from a page."""
        blocks = []

        if not self._should_extract_images:
            return blocks

        try:
            images = page.images
            for img in images:
                block = ImageBlock(
                    x0=img['x0'],
                    y0=img['top'],
                    x1=img['x1'],
                    y1=img['bottom'],
                    page_num=page_num,
                    width=img['width'],
                    height=img['height'],
                    format=img.get('format', 'unknown')
                )
                blocks.append(block)
        except Exception as e:
            print(f"Warning: Could not extract images from page {page_num}: {e}")

        return blocks

    def extract_tables_from_page(self, page, page_num: int) -> List[TableBlock]:
        """Extract tables from a page."""
        blocks = []

        if not self._should_extract_tables:
            return blocks

        try:
            tables = page.extract_tables()
            for table in tables:
                if not table:
                    continue

                # Get table bounding box
                # This is approximate - pdfplumber doesn't give exact positions
                rows = [[str(cell) if cell else '' for cell in row] for row in table]

                # Try to get table position from page
                bbox = page.find_tables()
                if bbox:
                    for t in bbox:
                        block = TableBlock(
                            x0=t.bbox[0],
                            y0=t.bbox[1],
                            x1=t.bbox[2],
                            y1=t.bbox[3],
                            page_num=page_num,
                            rows=rows
                        )
                        blocks.append(block)
                        break
                else:
                    # Fallback without position
                    block = TableBlock(
                        x0=0,
                        y0=0,
                        x1=0,
                        y1=0,
                        page_num=page_num,
                        rows=rows
                    )
                    blocks.append(block)
        except Exception as e:
            print(f"Warning: Could not extract tables from page {page_num}: {e}")

        return blocks

    def extract_page(self, page, page_num: int) -> PageContent:
        """Extract all content from a single page."""
        width = page.width
        height = page.height

        text_blocks = self.extract_text_blocks(page, page_num)
        image_blocks = self.extract_images_from_page(page, page_num)
        table_blocks = self.extract_tables_from_page(page, page_num)

        return PageContent(
            page_num=page_num,
            width=width,
            height=height,
            text_blocks=text_blocks,
            image_blocks=image_blocks,
            table_blocks=table_blocks
        )

    def extract_metadata(self, pdf) -> Dict[str, Any]:
        """Extract PDF metadata."""
        metadata = {}
        try:
            meta = pdf.metadata
            if meta:
                metadata = {
                    "title": meta.get('Title', ''),
                    "author": meta.get('Author', ''),
                    "subject": meta.get('Subject', ''),
                    "creator": meta.get('Creator', ''),
                    "producer": meta.get('Producer', ''),
                    "creation_date": str(meta.get('CreationDate', '')),
                    "modification_date": str(meta.get('ModDate', ''))
                }
        except Exception as e:
            print(f"Warning: Could not extract metadata: {e}")

        return metadata

    def extract(self, filepath: str) -> PDFDocument:
        """Extract content from a PDF file."""
        filename = os.path.basename(filepath)
        pages = []

        with pdfplumber.open(filepath) as pdf:
            num_pages = len(pdf.pages)
            metadata = self.extract_metadata(pdf)

            for i, page in enumerate(pdf.pages):
                page_content = self.extract_page(page, i + 1)
                pages.append(page_content)
                print(f"Extracted page {i + 1}/{num_pages}")

        return PDFDocument(
            filename=filename,
            num_pages=num_pages,
            metadata=metadata,
            pages=pages
        )

    def extract_text_only(self, filepath: str) -> str:
        """Extract plain text from a PDF file."""
        text_parts = []

        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)

        return '\n\n'.join(text_parts)


def main():
    """Command-line interface for PDF extraction."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract content from PDF files")
    parser.add_argument("input", help="Input PDF file path")
    parser.add_argument("-o", "--output", help="Output JSON file path")
    parser.add_argument("--no-images", action="store_true", help="Skip image extraction")
    parser.add_argument("--no-tables", action="store_true", help="Skip table extraction")
    parser.add_argument("--text-only", action="store_true", help="Output plain text only")

    args = parser.parse_args()

    extractor = PDFExtractor(
        extract_images=not args.no_images,
        extract_tables=not args.no_tables
    )

    if args.text_only:
        text = extractor.extract_text_only(args.input)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"Text saved to {args.output}")
        else:
            print(text)
    else:
        document = extractor.extract(args.input)

        if args.output:
            document.to_json(args.output)
            print(f"Document structure saved to {args.output}")
        else:
            print(json.dumps(document.to_dict(), indent=2))


if __name__ == "__main__":
    main()
