#!/usr/bin/env python3
"""
PDF Processing Script - Uses Overlay Method

This script processes PDFs using the overlay method which:
- Preserves images
- Maintains original layout
- Keeps tables and formatting
- Only modifies text styling
"""

import sys
import os
import json
import argparse

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from bionic_overlay import process_pdf_with_overlay
except ImportError as e:
    print(json.dumps({"success": False, "error": f"Import error: {e}. Please install requirements: pip install pdfplumber reportlab pypdf pikepdf"}))
    sys.exit(1)


def process_pdf(input_path, output_path, ratio=0.4, min_length=3, intensity="medium"):
    """Process PDF using overlay method - preserves layout and images."""
    try:
        result = process_pdf_with_overlay(
            input_path,
            output_path,
            emphasis_ratio=ratio,
            min_word_length=min_length,
            bold_intensity=intensity
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process PDF with bionic reading (overlay method)')
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("-o", "--output", required=True, help="Output PDF file")
    parser.add_argument("-r", "--ratio", type=float, default=0.4, help="Emphasis ratio (0.1-0.7)")
    parser.add_argument("-m", "--min-length", type=int, default=3, help="Min word length")
    parser.add_argument("-i", "--intensity", default="medium", help="Bold intensity: light, medium, heavy")
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
            print(f"\n✅ Success! Output: {result['output_path']}")
            print(f"📊 Stats: {result['statistics']}")
        else:
            print(f"\n❌ Error: {result['error']}")
            sys.exit(1)
