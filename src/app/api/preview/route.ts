import { NextRequest, NextResponse } from 'next/server';

function transformTextJS(
  text: string,
  emphasisRatio: number,
  minWordLength: number,
  boldIntensity: string
): string {
  const mult = boldIntensity === 'light' ? 0.8 : boldIntensity === 'heavy' ? 1.2 : 1.0;
  const effectiveRatio = Math.min(0.7, Math.max(0.2, emphasisRatio * mult));
  
  return text.replace(/[\w\u4e00-\u9fff]+/g, (word) => {
    if (word.length < minWordLength) return word;
    if (/[\u4e00-\u9fff]/.test(word[0])) {
      return `**${word[0]}**${word.slice(1)}`;
    }
    const boldChars = Math.max(1, Math.min(word.length - 1, Math.round(word.length * effectiveRatio)));
    return `**${word.slice(0, boldChars)}**${word.slice(boldChars)}`;
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { text, emphasisRatio = 0.4, minWordLength = 3, boldIntensity = 'medium' } = body;

    if (!text) {
      return NextResponse.json({ success: false, error: 'Text is required' }, { status: 400 });
    }

    const previewText = text.length > 5000 ? text.slice(0, 5000) + '...' : text;
    const transformed = transformTextJS(previewText, emphasisRatio, minWordLength, boldIntensity);

    return NextResponse.json({ success: true, original: previewText, transformed });
  } catch (error) {
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
