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
  await fs.mkdir(UPLOAD_DIR, { recursive: true });
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
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
    await fs.writeFile(inputPath, Buffer.from(bytes));

    const scriptPath = path.join(process.cwd(), 'scripts', 'process_pdf.py');
    const command = `python3 "${scriptPath}" "${inputPath}" -o "${outputPath}" -r ${emphasisRatio} -m ${minWordLength} -i ${boldIntensity} --json 2>&1`;

    console.log('Running:', command);

    let stdout = '';
    try {
      const result = await execAsync(command, { timeout: 300000 });
      stdout = result.stdout;
    } catch (e: any) {
      stdout = e.stdout || e.message;
    }

    console.log('Output:', stdout);
    await fs.unlink(inputPath).catch(() => {});

    const lines = stdout.trim().split('\n');
    let data = null;
    for (const line of lines.reverse()) {
      try {
        const parsed = JSON.parse(line);
        if (parsed.success !== undefined) { data = parsed; break; }
      } catch {}
    }

    if (!data) {
      return NextResponse.json({ success: false, error: 'No valid output. Check Python dependencies: pip install pdfplumber reportlab pypdf' }, { status: 500 });
    }

    if (!data.success) {
      return NextResponse.json({ success: false, error: data.error }, { status: 500 });
    }

    try { await fs.access(outputPath); } catch {
      return NextResponse.json({ success: false, error: 'Output file not created' }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      fileId,
      outputPath: `/api/download/${fileId}`,
      fileName: file.name.replace('.pdf', '_bionic.pdf'),
      statistics: data.statistics || {}
    });
  } catch (error) {
    console.error('Error:', error);
    return NextResponse.json({ success: false, error: String(error) }, { status: 500 });
  }
}
