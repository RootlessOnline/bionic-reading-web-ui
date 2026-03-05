#!/usr/bin/env python3
"""
Bionic Reading PDF Overlay Generator

Creates a PDF overlay with bionic reading enhancement.
The overlay is merged onto the original PDF, preserving:
- Images
- Tables
- Original layout
- All formatting
"""

import pdfplumber
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfont import TTFont
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import re
import os
import tempfile

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    from PyPDF2 import PdfReader, PdfWriter


# Font paths with fallbacks
FONT_PATHS = {
    'normal': [
        '/usr/share/fonts/truetype/english/calibri-regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
    ],
    'bold': [
        '/usr/share/fonts/truetype/english/calibri-bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    ],
}


class FontManager:
    """Manage font registration with fallbacks."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if FontManager._initialized:
            return
        
        self.fonts = {'normal': 'Helvetica', 'bold': 'Helvetica-Bold'}
        
        # Try to register fonts
        for font_type, paths in FONT_PATHS.items():
            for path in paths:
                if os.path.exists(path):
                    try:
                        font_name = f"Bionic_{font_type}"
                        pdfmetrics.registerFont(TTFont(font_name, path))
                        self.fonts[font_type] = font_name
                        print(f"Registered font: {font_name}")
                        break
                    except Exception as e:
                        print(f"Warning: Could not register {path}: {e}")
        
        FontManager._initialized = True
    
    def get_font(self, is_bold: bool = False) -> str:
        return self.fonts['bold'] if is_bold else self.fonts['normal']


def is_cjk(char: str) -> bool:
    """Check if character is CJK."""
    if not char:
        return False
    code = ord(char)
    return 0x4E00 <= code <= 0x9FFF


def transform_word_bionic(word: str, ratio: float, intensity: str) -> Tuple[str, str]:
    """
    Transform a word for bionic reading.
    Returns (bold_part, normal_part).
    """
    if not word or len(word) < 2:
        return (word, "")
    
    # Adjust ratio based on intensity
    intensity_mult = {'light': 0.8, 'medium': 1.0, 'heavy': 1.2}.get(intensity, 1.0)
    effective_ratio = min(0.7, max(0.2, ratio * intensity_mult))
    
    # For CJK, bold just the first character
    if is_cjk(word[0]):
        return (word[0], word[1:])
    
    # Calculate bold portion
    bold_count = max(1, min(len(word) - 1, round(len(word) * effective_ratio)))
    
    return (word[:bold_count], word[bold_count:])


def create_bionic_overlay(
    input_pdf_path: str,
    output_path: str,
    emphasis_ratio: float = 0.4,
    min_word_length: int = 3,
    bold_intensity: str = "medium"
) -> str:
    """
    Create a PDF overlay with bionic reading enhancement.
    
    This creates a transparent PDF with bold characters positioned
    exactly where the original text is, so when merged, the bold
    text overlays the original.
    """
    font_mgr = FontManager()
    
    with pdfplumber.open(input_pdf_path) as pdf:
        overlay_canvas = canvas.Canvas(output_path)
        
        for page_num, page in enumerate(pdf.pages):
            page_width = page.width
            page_height = page.height
            
            overlay_canvas.setPageSize((page_width, page_height))
            
            # Get all characters with positions
            chars = page.chars
            
            if not chars:
                overlay_canvas.showPage()
                continue
            
            # Group characters into words by line and position
            words_by_line = _group_chars_by_line(chars)
            
            for line_chars in words_by_line:
                words = _split_line_into_words(line_chars)
                
                for word_chars in words:
                    if not word_chars:
                        continue
                    
                    word_text = ''.join(c.char for c in word_chars)
                    word_len = len(word_text)
                    
                    # Skip short words
                    if word_len < min_word_length:
                        continue
                    
                    # Get transformation
                    bold_part, normal_part = transform_word_bionic(
                        word_text, emphasis_ratio, bold_intensity
                    )
                    
                    if not bold_part:
                        continue
                    
                    # Draw bold characters at their positions
                    char_index = 0
                    for char in word_chars:
                        if char_index < len(bold_part):
                            # Draw this character in bold
                            x = char.x0
                            y = page_height - char.y0 - char.size * 0.15
                            
                            # Use slightly larger font to cover original
                            font_size = char.size * 1.02
                            
                            overlay_canvas.setFont(
                                font_mgr.get_font(is_bold=True),
                                font_size
                            )
                            overlay_canvas.drawString(x, y, char.char)
                        
                        char_index += 1
            
            overlay_canvas.showPage()
            
            if (page_num + 1) % 10 == 0:
                print(f"Processed {page_num + 1}/{len(pdf.pages)} pages")
        
        overlay_canvas.save()
        print(f"Created overlay: {output_path}")
    
    return output_path


def _group_chars_by_line(chars: List, line_threshold: float = 2.0) -> List[List]:
    """Group characters by line based on y-position."""
    if not chars:
        return []
    
    lines = {}
    for char in chars:
        y_key = round(char.y0 / line_threshold) * line_threshold
        if y_key not in lines:
            lines[y_key] = []
        lines[y_key].append(char)
    
    # Sort each line by x position and return sorted by y (top to bottom)
    result = []
    for y_key in sorted(lines.keys(), reverse=True):
        line_chars = sorted(lines[y_key], key=lambda c: c.x0)
        result.append(line_chars)
    
    return result


def _split_line_into_words(chars: List, gap_threshold: float = 0.25) -> List[List]:
    """Split a line of characters into words."""
    if not chars:
        return []
    
    words = []
    current_word = [chars[0]]
    last_char = chars[0]
    
    for char in chars[1:]:
        gap = char.x0 - last_char.x1
        
        # Word boundary: space, large gap, or font change
        is_space = char.char.isspace() or last_char.char.isspace()
        is_large_gap = gap > last_char.size * gap_threshold
        
        if is_space or is_large_gap:
            if current_word and not all(c.char.isspace() for c in current_word):
                words.append(current_word)
            current_word = [] if is_space else [char]
        else:
            current_word.append(char)
        
        last_char = char
    
    if current_word and not all(c.char.isspace() for c in current_word):
        words.append(current_word)
    
    return words


def merge_overlay_with_original(
    original_pdf_path: str,
    overlay_pdf_path: str,
    output_path: str
) -> str:
    """Merge overlay PDF with original, using overlay to enhance text."""
    
    original = PdfReader(original_pdf_path)
    overlay = PdfReader(overlay_pdf_path)
    writer = PdfWriter()
    
    for i, (orig_page, overlay_page) in enumerate(zip(original.pages, overlay.pages)):
        # Merge overlay onto original
        orig_page.merge_page(overlay_page)
        writer.add_page(orig_page)
    
    # Copy metadata
    try:
        meta = original.metadata or {}
        writer.add_metadata({
            '/Title': meta.get('/Title', 'Bionic Enhanced Document'),
            '/Author': meta.get('/Author', 'Z.ai'),
            '/Creator': 'Z.ai Bionic Reading Converter',
            '/Producer': 'Z.ai'
        })
    except:
        pass
    
    with open(output_path, 'wb') as f:
        writer.write(f)
    
    print(f"Merged PDF saved: {output_path}")
    return output_path


def process_pdf_with_overlay(
    input_path: str,
    output_path: str,
    emphasis_ratio: float = 0.4,
    min_word_length: int = 3,
    bold_intensity: str = "medium"
) -> Dict:
    """
    Process PDF using overlay method - preserves layout and images.
    
    This is the recommended approach for best results.
    """
    # Create temporary overlay file
    overlay_fd, overlay_path = tempfile.mkstemp(suffix='.pdf')
    os.close(overlay_fd)
    
    try:
        # Step 1: Create overlay with bold characters
        print(f"Creating bionic overlay for: {input_path}")
        create_bionic_overlay(
            input_path,
            overlay_path,
            emphasis_ratio,
            min_word_length,
            bold_intensity
        )
        
        # Step 2: Merge with original
        print("Merging overlay with original PDF...")
        merge_overlay_with_original(input_path, overlay_path, output_path)
        
        # Get statistics
        with pdfplumber.open(input_path) as pdf:
            total_words = 0
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    total_words += len(text.split())
            
            stats = {
                'pages': len(pdf.pages),
                'estimated_words': total_words
            }
        
        return {
            'success': True,
            'output_path': output_path,
            'statistics': stats
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }
    
    finally:
        # Cleanup temp file
        if os.path.exists(overlay_path):
            try:
                os.remove(overlay_path)
            except:
                pass


if __name__ == '__main__':
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Process PDF with bionic overlay')
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("-o", "--output", required=True, help="Output PDF file")
    parser.add_argument("-r", "--ratio", type=float, default=0.4, help="Emphasis ratio")
    parser.add_argument("-m", "--min-length", type=int, default=3, help="Min word length")
    parser.add_argument("-i", "--intensity", default="medium", help="light/medium/heavy")
    parser.add_argument("--json", action="store_true", help="JSON output")
    
    args = parser.parse_args()
    
    result = process_pdf_with_overlay(
        args.input,
        args.output,
        args.ratio,
        args.min_length,
        args.intensity
    )
    
    if args.json:
        print(json.dumps(result))
    else:
        if result['success']:
            print(f"\n✅ Success! Output: {result['output_path']}")
            print(f"📊 Stats: {result['statistics']}")
        else:
            print(f"\n❌ Error: {result['error']}")
