#!/usr/bin/env python3
"""
PDF Processing Script for Web UI
Wraps the core processing with JSON output for API consumption.
"""

import sys
import os
import json
import argparse

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from bionic_reader import BionicReader, BionicConfig
    from pdf_extractor import PDFExtractor, PDFDocument
    from pdf_generator import PDFGenerator, GeneratorConfig
except ImportError as e:
    print(json.dumps({"success": False, "error": f"Import error: {e}"}))
    sys.exit(1)

def process_pdf(input_path, output_path, ratio=0.4, min_length=3, intensity="medium"):
    """Process PDF and return JSON result."""
    try:
        # Extract
        extractor = PDFExtractor(extract_images=False, extract_tables=False)
        document = extractor.extract(input_path)
        
        # Create config
        bionic_config = BionicConfig(
            emphasis_ratio=ratio,
            min_word_length=min_length,
            bold_intensity=intensity
        )
        
        # Generate
        generator_config = GeneratorConfig(
            output_path=output_path,
            apply_bionic=True,
            bionic_config=bionic_config,
            preserve_layout=True
        )
        
        generator = PDFGenerator(generator_config)
        generator.generate_simple_pdf(document)
        
        # Statistics
        total_words = sum(
            len(block.text.split())
            for page in document.pages
            for block in page.text_blocks
        )
        
        return {
            "success": True,
            "output_path": output_path,
            "statistics": {
                "pages": document.num_pages,
                "text_blocks": sum(len(p.text_blocks) for p in document.pages),
                "estimated_words": total_words
            }
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input PDF")
    parser.add_argument("-o", "--output", required=True, help="Output PDF")
    parser.add_argument("-r", "--ratio", type=float, default=0.4)
    parser.add_argument("-m", "--min-length", type=int, default=3)
    parser.add_argument("-i", "--intensity", default="medium")
    parser.add_argument("--json", action="store_true")
    
    args = parser.parse_args()
    
    result = process_pdf(
        args.input,
        args.output,
        args.ratio,
        args.min_length,
        args.intensity
    )
    
    print(json.dumps(result))
