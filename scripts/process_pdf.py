#!/usr/bin/env python3
"""
Bionic Reading PDF Processor - Simplified Version

Processes PDFs while preserving images, tables, and layout.
Uses overlay method for best results.
"""

import sys
import os
import json
import argparse
import tempfile

try:
    import pdfplumber
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfont import TTFont
except ImportError as e:
    print(json.dumps({"success": False, "error": f"Missing dependency: {e}. Run: pip install pdfplumber reportlab"}))
    sys.exit(1)

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    try:
        from PyPDF2 import PdfReader, PdfWriter
    except ImportError:
        print(json.dumps({"success": False, "error": "Missing pypdf. Run: pip install pypdf"}))
        sys.exit(1)


# Font paths
FONT_PATHS = {
    'normal': [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/english/calibri-regular.ttf',
    ],
    'bold': [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        '/usr/share/fonts/truetype/english/calibri-bold.ttf',
    ],
}


def get_fonts():
    """Get available fonts with fallbacks."""
    fonts = {'normal': 'Helvetica', 'bold': 'Helvetica-Bold'}
    
    for font_type, paths in FONT_PATHS.items():
        for path in paths:
            if os.path.exists(path):
                try:
                    name = f"Bionic_{font_type}"
                    pdfmetrics.registerFont(TTFont(name, path))
                    fonts[font_type] = name
                    break
                except:
                    pass
    
    return fonts


def is_cjk(char):
    """Check if character is CJK."""
    if not char:
        return False
    code = ord(char)
    return 0x4E00 <= code <= 0x9FFF


def create_overlay(input_path, output_path, ratio=0.4, min_len=3, intensity="medium"):
    """Create overlay PDF with bold text at exact positions."""
    
    fonts = get_fonts()
    intensity_mult = {'light': 0.8, 'medium': 1.0, 'heavy': 1.2}.get(intensity, 1.0)
    effective_ratio = min(0.7, max(0.2, ratio * intensity_mult))
    
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
            
            # Group by lines
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
                current = [line_chars[0]] if line_chars else []
                
                for i in range(1, len(line_chars)):
                    gap = line_chars[i].x0 - line_chars[i-1].x1
                    is_space = line_chars[i].char.isspace() or line_chars[i-1].char.isspace()
                    
                    if is_space or gap > line_chars[i-1].size * 0.3:
                        if current and not all(x.char.isspace() for x in current):
                            words.append(current)
                        current = [] if is_space else [line_chars[i]]
                    else:
                        current.append(line_chars[i])
                
                if current and not all(x.char.isspace() for x in current):
                    words.append(current)
                
                # Process words
                for word_chars in words:
                    word = ''.join(x.char for x in word_chars)
                    
                    if len(word) < min_len:
                        continue
                    
                    # Calculate bold portion
                    if is_cjk(word[0]):
                        bold_count = 1
                    else:
                        bold_count = max(1, min(len(word) - 1, round(len(word) * effective_ratio)))
                    
                    # Draw bold characters
                    for i, char in enumerate(word_chars):
                        if i < bold_count:
                            x = char.x0
                            y = height - char.y0 - char.size * 0.15
                            c.setFont(fonts['bold'], char.size * 1.02)
                            c.drawString(x, y, char.char)
            
            c.showPage()
            
            if (page_num + 1) % 5 == 0:
                print(f"Processed {page_num + 1}/{len(pdf.pages)} pages", file=sys.stderr)
        
        c.save()


def merge_pdfs(original_path, overlay_path, output_path):
    """Merge overlay onto original PDF."""
    
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
        create_overlay(input_path, overlay_path, ratio, min_len, intensity)
        merge_pdfs(input_path, overlay_path, output_path)
        
        # Get stats
        with pdfplumber.open(input_path) as pdf:
            words = sum(len(p.extract_text().split()) for p in pdf.pages if p.extract_text())
        
        return {
            "success": True,
            "output_path": output_path,
            "statistics": {"pages": len(pdf.pages), "estimated_words": words}
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    finally:
        if os.path.exists(overlay_path):
            os.remove(overlay_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("-r", "--ratio", type=float, default=0.4)
    parser.add_argument("-m", "--min-length", type=int, default=3)
    parser.add_argument("-i", "--intensity", default="medium")
    parser.add_argument("--json", action="store_true")
    
    args = parser.parse_args()
    
    result = process_pdf(args.input, args.output, args.ratio, args.min_length, args.intensity)
    
    if args.json:
        print(json.dumps(result))
    else:
        if result['success']:
            print(f"✅ Done: {result['output_path']}")
        else:
            print(f"❌ Error: {result['error']}")
            sys.exit(1)
