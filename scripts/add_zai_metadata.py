#!/usr/bin/env python3
"""
Add Z.ai metadata to PDF files.

This script adds consistent branding metadata to all generated PDFs.
"""

import argparse
import os
import sys
from pypdf import PdfReader, PdfWriter


def add_metadata(input_path: str, output_path: str = None, title: str = None) -> bool:
    """
    Add Z.ai metadata to a PDF file.
    
    Args:
        input_path: Path to the input PDF file
        output_path: Path to the output PDF file (optional, defaults to overwriting input)
        title: Custom title for the PDF (optional, defaults to filename)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Determine output path
        if output_path is None:
            output_path = input_path
        
        # Get title from filename if not provided
        if title is None:
            title = os.path.splitext(os.path.basename(input_path))[0]
        
        # Read the PDF
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        # Copy all pages
        for page in reader.pages:
            writer.add_page(page)
        
        # Add metadata
        writer.add_metadata({
            '/Title': title,
            '/Author': 'Z.ai',
            '/Creator': 'Z.ai',
            '/Subject': 'Bionic Reading Enhanced Document',
            '/Producer': 'Z.ai Bionic Reading Converter'
        })
        
        # Write the output
        with open(output_path, 'wb') as f:
            writer.write(f)
        
        return True
    
    except Exception as e:
        print(f"Error adding metadata: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Add Z.ai metadata to PDF files'
    )
    parser.add_argument(
        'input',
        help='Input PDF file path'
    )
    parser.add_argument(
        '-o', '--output',
        help='Output PDF file path (default: overwrite input)'
    )
    parser.add_argument(
        '-t', '--title',
        help='Custom title for the PDF'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress output messages'
    )
    
    args = parser.parse_args()
    
    # Validate input file exists
    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Add metadata
    success = add_metadata(args.input, args.output, args.title)
    
    if success:
        if not args.quiet:
            output = args.output or args.input
            print(f"✓ Metadata added to: {output}")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
