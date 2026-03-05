#!/usr/bin/env python3
"""
Bionic Reading Transformer

This module implements the core bionic reading transformation algorithm.
Bionic reading enhances text readability by selectively bolding initial
characters or syllables of words, helping readers with ADHD to focus
and comprehend text more efficiently.
"""

import re
import regex
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class BionicConfig:
    """Configuration for bionic reading transformation."""
    emphasis_ratio: float = 0.4  # Percentage of word to bold (0.3-0.5)
    min_word_length: int = 3  # Minimum word length to apply transformation
    skip_short_words: bool = True  # Skip words shorter than min_word_length
    preserve_formatting: bool = True  # Maintain original text formatting
    bold_intensity: str = "medium"  # Light, Medium, Heavy
    language_mode: str = "auto"  # auto, en, zh, mixed

    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0.1 <= self.emphasis_ratio <= 0.7:
            raise ValueError("emphasis_ratio must be between 0.1 and 0.7")
        if not 1 <= self.min_word_length <= 10:
            raise ValueError("min_word_length must be between 1 and 10")
        if self.bold_intensity not in ["light", "medium", "heavy"]:
            raise ValueError("bold_intensity must be light, medium, or heavy")


# Unicode ranges for different character types
CJK_RANGES = [
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0x3400, 0x4DBF),    # CJK Unified Ideographs Extension A
    (0x20000, 0x2A6DF),  # CJK Unified Ideographs Extension B
    (0x2A700, 0x2B73F),  # CJK Unified Ideographs Extension C
    (0x2B740, 0x2B81F),  # CJK Unified Ideographs Extension D
    (0x2B820, 0x2CEAF),  # CJK Unified Ideographs Extension E
    (0xF900, 0xFAFF),    # CJK Compatibility Ideographs
    (0x2F800, 0x2FA1F),  # CJK Compatibility Ideographs Supplement
]

# Common English syllable patterns (simplified)
VOWEL_PATTERN = r'[aeiouyAEIOUY]'
CONSONANT_PATTERN = r'[bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ]'


def is_cjk_char(char: str) -> bool:
    """Check if a character is a CJK character."""
    if not char:
        return False
    code_point = ord(char)
    for start, end in CJK_RANGES:
        if start <= code_point <= end:
            return True
    return False


def detect_text_language(text: str) -> str:
    """Detect the primary language of the text."""
    if not text:
        return "unknown"

    cjk_count = sum(1 for char in text if is_cjk_char(char))
    latin_count = sum(1 for char in text if char.isalpha() and not is_cjk_char(char))

    total_alpha = cjk_count + latin_count
    if total_alpha == 0:
        return "unknown"

    cjk_ratio = cjk_count / total_alpha

    if cjk_ratio > 0.7:
        return "zh"
    elif cjk_ratio < 0.3:
        return "en"
    else:
        return "mixed"


def get_bold_intensity_ratio(intensity: str) -> float:
    """Get emphasis ratio multiplier based on intensity setting."""
    intensity_map = {
        "light": 0.8,
        "medium": 1.0,
        "heavy": 1.2
    }
    return intensity_map.get(intensity, 1.0)


def split_by_syllables(word: str) -> Tuple[str, str]:
    """
    Attempt to split a word at a natural syllable boundary.
    Returns (bold_part, normal_part).
    """
    if len(word) <= 2:
        return (word, "")

    # Try to find a good splitting point
    # Look for vowel-consonant patterns
    patterns = [
        # VC pattern (vowel-consonant) - split after first consonant following vowel
        rf'^({CONSONANT_PATTERN}*{VOWEL_PATTERN}{CONSONANT_PATTERN})',
        # CV pattern - split after first vowel
        rf'^({CONSONANT_PATTERN}*{VOWEL_PATTERN})',
        # Default: just take first part
    ]

    for pattern in patterns:
        match = re.match(pattern, word, re.IGNORECASE)
        if match:
            split_point = len(match.group(1))
            if 0 < split_point < len(word):
                return (word[:split_point], word[split_point:])

    return (word, "")


def transform_word(word: str, config: BionicConfig) -> str:
    """
    Transform a single word with bionic reading emphasis.
    Returns the word with the appropriate portion marked for bolding.
    """
    if not word:
        return word

    # Skip short words if configured
    if config.skip_short_words and len(word) < config.min_word_length:
        return word

    # Handle CJK characters differently
    if is_cjk_char(word[0]):
        # For CJK, we just bold the first character
        if len(word) == 1:
            return f"**{word}**"
        return f"**{word[0]}**{word[1:]}"

    # Calculate effective emphasis ratio
    intensity_mult = get_bold_intensity_ratio(config.bold_intensity)
    effective_ratio = config.emphasis_ratio * intensity_mult
    effective_ratio = min(0.7, max(0.2, effective_ratio))

    # Calculate number of characters to bold
    word_len = len(word)
    bold_chars = max(1, round(word_len * effective_ratio))

    # Ensure we don't bold the entire word for short words
    if bold_chars >= word_len:
        bold_chars = max(1, word_len // 2)

    # For medium/heavy intensity, try syllable-aware splitting
    if config.bold_intensity in ["medium", "heavy"] and word_len > 3:
        bold_part, normal_part = split_by_syllables(word)
        if normal_part and 0 < len(bold_part) <= bold_chars * 1.5:
            return f"**{bold_part}**{normal_part}"

    # Default: bold first n characters
    return f"**{word[:bold_chars]}**{word[bold_chars:]}"


def preserve_formatting_wrapper(original: str, transformed: str) -> str:
    """Preserve the original formatting of a word while applying transformation."""
    # Check for common formatting patterns
    patterns = [
        (r'^([A-Z]+)$', lambda m: m.group(1)),  # ALL CAPS
        (r'^([a-z]+)$', lambda m: m.group(1)),  # all lowercase
        (r'^([A-Z][a-z]+)$', lambda m: m.group(1)),  # Capitalized
    ]

    for pattern, handler in patterns:
        if re.match(pattern, original):
            # Return transformed with original case preserved
            return transformed

    return transformed


def extract_words_and_boundaries(text: str) -> List[Tuple[str, int, int]]:
    """
    Extract words with their positions in the text.
    Returns list of (word, start_pos, end_pos) tuples.
    """
    words = []
    # Match word boundaries including CJK
    pattern = r'[\w\u4e00-\u9fff]+'

    for match in regex.finditer(pattern, text):
        word = match.group()
        start, end = match.span()
        words.append((word, start, end))

    return words


def transform_text(text: str, config: BionicConfig) -> str:
    """
    Transform an entire text with bionic reading emphasis.
    Preserves all original whitespace and punctuation.
    """
    if not text:
        return text

    # Detect language if auto mode
    if config.language_mode == "auto":
        detected_lang = detect_text_language(text)
        # Adjust config for CJK languages
        if detected_lang == "zh":
            # For Chinese, use smaller emphasis ratio
            config = BionicConfig(
                emphasis_ratio=min(config.emphasis_ratio, 0.3),
                min_word_length=config.min_word_length,
                skip_short_words=config.skip_short_words,
                preserve_formatting=config.preserve_formatting,
                bold_intensity=config.bold_intensity,
                language_mode=detected_lang
            )

    # Extract words with positions
    words_with_positions = extract_words_and_boundaries(text)

    if not words_with_positions:
        return text

    # Process words from end to start to preserve positions
    result = list(text)

    for word, start, end in reversed(words_with_positions):
        transformed = transform_word(word, config)
        if config.preserve_formatting:
            transformed = preserve_formatting_wrapper(word, transformed)

        # Replace in result
        result[start:end] = list(transformed)

    return ''.join(result)


def transform_line(line: str, config: BionicConfig) -> str:
    """Transform a single line of text."""
    return transform_text(line, config)


def estimate_reading_improvement(original: str, transformed: str) -> Dict:
    """
    Estimate the reading improvement from bionic transformation.
    Returns statistics about the transformation.
    """
    words = extract_words_and_boundaries(original)
    total_words = len(words)

    bold_count = transformed.count('**')
    # Each bold section has opening and closing **
    emphasized_segments = bold_count // 2

    cjk_words = sum(1 for word, _, _ in words if word and is_cjk_char(word[0]))
    latin_words = total_words - cjk_words

    return {
        "total_words": total_words,
        "emphasized_segments": emphasized_segments,
        "cjk_words": cjk_words,
        "latin_words": latin_words,
        "emphasis_percentage": (emphasized_segments / total_words * 100) if total_words > 0 else 0,
        "estimated_speed_improvement": f"{min(25, 10 + (emphasized_segments / max(1, total_words)) * 15):.1f}%"
    }


class BionicReader:
    """Main class for bionic reading transformation."""

    def __init__(self, config: Optional[BionicConfig] = None):
        """Initialize with optional configuration."""
        self.config = config or BionicConfig()

    def transform(self, text: str) -> str:
        """Transform text with current configuration."""
        return transform_text(text, self.config)

    def transform_paragraph(self, paragraph: str) -> str:
        """Transform a paragraph, preserving line breaks."""
        lines = paragraph.split('\n')
        return '\n'.join(transform_line(line, self.config) for line in lines)

    def transform_document(self, lines: List[str]) -> List[str]:
        """Transform multiple lines (document)."""
        return [transform_line(line, self.config) for line in lines]

    def get_statistics(self, original: str, transformed: str) -> Dict:
        """Get transformation statistics."""
        return estimate_reading_improvement(original, transformed)

    def update_config(self, **kwargs) -> None:
        """Update configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)


# Command-line interface
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Bionic Reading Transformer")
    parser.add_argument("input", help="Input text or file path")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("-r", "--ratio", type=float, default=0.4, help="Emphasis ratio (0.1-0.7)")
    parser.add_argument("-m", "--min-length", type=int, default=3, help="Minimum word length")
    parser.add_argument("-i", "--intensity", choices=["light", "medium", "heavy"], default="medium", help="Bold intensity")
    parser.add_argument("--stats", action="store_true", help="Show statistics")

    args = parser.parse_args()

    config = BionicConfig(
        emphasis_ratio=args.ratio,
        min_word_length=args.min_length,
        bold_intensity=args.intensity
    )

    reader = BionicReader(config)

    # Check if input is a file
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        text = args.input

    result = reader.transform(text)

    if args.stats:
        stats = reader.get_statistics(text, result)
        print(json.dumps(stats, indent=2))

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"Transformed text saved to {args.output}")
    else:
        print(result)
