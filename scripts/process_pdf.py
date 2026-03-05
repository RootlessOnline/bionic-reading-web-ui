#!/usr/bin/env python3
"""
Bionic Reading PDF Processor - Self-contained version

Processes PDFs while preserving images, tables, and layout.
All code is inline - no external module imports needed.
"""

import sys
import os
import json
import argparse
import tempfile

# Check dependencies first
try:
    import pdfplumber
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfont import TTFont
except ImportError as e:
    print(json.dumps({
        "success": False, 
        "error": f"Missing dependency: {e}. Run: pip install pdfplumber reportlab pypdf"
    }))
    sys.exit(1)

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        print(json.dumps({
            "success": False,
            "error": "Missing pypdf. Run: pip install pypdf"
        }))
        sys.exit(1)


# ============ FONT MANAGEMENT ============

FONT_PATHS = {
    'normal': [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf',
        '/usr/share/fonts/truetype/english/calibri-regular.ttf',
    ],
    'bold': [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf',
        '/usr/share/fonts/truetype/english/calibri-bold.ttf',
    ],
}

_fonts_registered = False
_fonts = {'normal': 'Helvetica', 'bold': 'Helvetica-Bold'}

def register_fonts():
    """Register fonts with fallbacks."""
    global _fonts_registered, _fonts
    if _fonts_registered:
        return
    
    for font_type, paths in FONT_PATHS.items():
        for path in paths:
            if os.path.exists(path):
                try:
                    name = f"Bionic_{font_type}"
                    pdfmetrics.registerFont(TTFont(name, path))
                    _fonts[font_type] = name
                    break
                except:
                    pass
    
    _fonts_registered = True


def get_font(is_bold=False):
    """Get font name."""
    register_fonts()
    return _fonts['bold'] if is_bold else _fonts['normal']


# ============ BIONIC TRANSFORMATION ============

def is_cjk(char):
    """Check if character is CJK."""
    if not char:
        return False
    code = ord(char)
    return 0x4E00 <= code <= 0x9FFF


def get_bold_count(word, ratio, intensity):
    """Calculate how many characters to bold."""
    if not word:
        return 0
    
    intensity_mult = {'light': 0.8, 'medium': 1.0, 'heavy': 1.2}.get(intensity, 1.0)
    effective_ratio = min(0.7, max(0.2, ratio * intensity_mult))
    
    if is_cjk(word[0]):
        return 1
    
    return max(1, min(len(word) - 1, round(len(word) * effective_ratio)))


# ============ PDF PROCESSING ============

def create_overlay(input_path, output_path, ratio=0.4, min_len=3, intensity="medium"):
    """Create overlay PDF with bold characters."""
    
    with pdfplumber.open(input_path) as pdf:
        c = canvas.Canvas(output_path)
        
        for page_num, page in enumerate(pdf.pages):
            width = page.width
            height = page.height
            c.setPageSize((width, height))
            
            chars = page.chars
            if not chars:
                c.showPage()
                continue
            
            # Group chars by line (y-position)
            lines = {}
            for char in chars:
                y_key = round(char.y0 / 2) * 2
                if y_key not in lines:
                    lines[y_key] = []
                lines[y_key].append(char)
            
            # Process each line
            for y_key in sorted(lines.keys(), reverse=True):
                line_chars = sorted(lines[y_key], key=lambda x: x.x0)
                
                # Split into words
                words = []
                current_word = []
                last_char = None
                
                for char in line_chars:
                    is_space = char.char.isspace()
                    
                    if last_char:
                        gap = char.x0 - last_char.x1
                        is_new_word = gap > last_char.size * 0.25 or is_space
                    else:
                        is_new_word = True
                    
                    if is_new_word:
                        if current_word and not all(x.char.isspace() for x in current_word):
                            words.append(current_word)
                        current_word = [] if is_space else [char]
                    else:
                        current_word.append(char)
                    
                    last_char = char
                
                if current_word and not all(x.char.isspace() for x in current_word):
                    words.append(current_word)
                
                # Process each word
                for word_chars in words:
                    word_text = ''.join(x.char for x in word_chars)
                    
                    if len(word_text) < min_len:
                        continue
                    
                    bold_count = get_bold_count(word_text, ratio, intensity)
                    
                    # Draw bold characters
                    for i, char in enumerate(word_chars):
                        if i < bold_count:
                            x = char.x0
                            y = height - char.y0 - char.size * 0.15
                            c.setFont(get_font(is_bold=True), char.size * 1.02)
                            c.drawString(x, y, char.char)
            
            c.showPage()
            
            if (page_num + 1) % 10 == 0:
                print(f"Processed {page_num + 1}/{len(pdf.pages)} pages", file=sys.stderr)
        
        c.save()
        return True


def merge_pdfs(original_path, overlay_path, output_path):
    """Merge overlay onto original."""
    
    original = PdfReader(original_path)
    overlay = PdfReader(overlay_path)
    writer = PdfWriter()
    
    for i, (orig, over) in enumerate(zip(original.pages, overlay.pages)):
        orig.merge_page(over)
        writer.add_page(orig)
    
    try:
        writer.add_metadata({
            '/Title': 'Bionic Enhanced Document',
            '/Author': 'Z.ai',
            '/Creator': 'Z.ai Bionic Converter'
        })
    except:
        pass
    
    with open(output_path, 'wb') as f:
        writer.write(f)


def process_pdf(input_path, output_path, ratio=0.4, min_len=3, intensity="medium"):
    """Main processing function."""
    
    # Create temp overlay
    fd, overlay_path = tempfile.mkstemp(suffix='.pdf')
    os.close(fd)
    
    try:
        print(f"Processing: {input_path}", file=sys.stderr)
        create_overlay(input_path, overlay_path, ratio, min_len, intensity)
        merge_pdfs(input_path, overlay_path, output_path)
        
        # Get stats
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
            "success": True,
            "output_path": output_path,
            "statistics": stats
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {"success": False, "error": str(e)}
    
    finally:
        if os.path.exists(overlay_path):
            try:
                os.remove(overlay_path)
            except:
                pass


# ============ MAIN ============

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process PDF with bionic reading')
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("-o", "--output", required=True, help="Output PDF file")
    parser.add_argument("-r", "--ratio", type=float, default=0.4, help="Emphasis ratio (0.1-0.7)")
    parser.add_argument("-m", "--min-length", type=int, default=3, help="Min word length")
    parser.add_argument("-i", "--intensity", default="medium", help="light/medium/heavy")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    result = process_pdf(
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
            print(f"Done: {result['output_path']}")
            print(f"Stats: {result['statistics']}")
        else:
            print(f"Error: {result['error']}")
            sys.exit(1)
