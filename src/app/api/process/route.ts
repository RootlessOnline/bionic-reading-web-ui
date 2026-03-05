import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

const execAsync = promisify(exec);

const UPLOAD_DIR = '/tmp/bionic-uploads';
const OUTPUT_DIR = '/tmp/bionic-output';

async function ensureDirectories() {
  try {
    await fs.mkdir(UPLOAD_DIR, { recursive: true });
    await fs.mkdir(OUTPUT_DIR, { recursive: true });
  } catch (error) {
    console.error('Error creating directories:', error);
  }
}

export async function POST(request: NextRequest) {
  try {
    await ensureDirectories();

    const formData = await request.formData();
    const file = formData.get('file') as File;
    const emphasisRatio = parseFloat(formData.get('emphasisRatio') as string) || 0.4;
    const minWordLength = parseInt(formData.get('minWordLength') as string) || 3;
    const boldIntensity = (formData.get('boldIntensity') as string) || 'medium';

    if (!file) {
      return NextResponse.json({ success: false, error: 'No file provided' }, { status: 400 });
    }

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      return NextResponse.json({ success: false, error: 'File must be a PDF' }, { status: 400 });
    }

    const fileId = uuidv4();
    const inputPath = path.join(UPLOAD_DIR, `${fileId}_input.pdf`);
    const outputPath = path.join(OUTPUT_DIR, `${fileId}_bionic.pdf`);

    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);
    await fs.writeFile(inputPath, buffer);

    const scriptPath = path.join(process.cwd(), 'scripts', 'process_pdf.py');
    const command = `python3 "${scriptPath}" "${inputPath}" -o "${outputPath}" -r ${emphasisRatio} -m ${minWordLength} -i ${boldIntensity} --json`;

    const { stdout } = await execAsync(command, { timeout: 300000, maxBuffer: 50 * 1024 * 1024 });

    const lines = stdout.trim().split('\n');
    let result = null;

    for (const line of lines.reverse()) {
      try {
        const parsed = JSON.parse(line);
        if (parsed.success !== undefined) {
          result = parsed;
          break;
        }
      } catch {}
    }

    if (!result) result = { success: true, output_path: outputPath };

    try { await fs.unlink(inputPath); } catch {}

    if (result.success) {
      return NextResponse.json({
        success: true,
        fileId,
        outputPath: `/api/download/${fileId}`,
        fileName: file.name.replace('.pdf', '_bionic.pdf'),
        statistics: result.statistics || {}
      });
    } else {
      return NextResponse.json({ success: false, error: result.error }, { status: 500 });
    }
  } catch (error) {
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
