import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';
import { v4 as uuidv4 } from 'uuid';

const execAsync = promisify(exec);

const UPLOAD_DIR = '/tmp/bionic-uploads';
const OUTPUT_DIR = '/tmp/bionic-output';

// Use venv Python if available, fallback to system Python
function getPythonPath(): string {
  const possiblePaths = [
    // Check for venv in current directory
    path.join(process.cwd(), 'venv', 'bin', 'python3'),
    path.join(process.cwd(), 'venv', 'bin', 'python'),
    // Check home directory venvs
    path.join(process.env.HOME || '', 'bionic-reading-converter', 'venv', 'bin', 'python3'),
    path.join(process.env.HOME || '', 'bionic-reading-web-ui', 'venv', 'bin', 'python3'),
    // System fallback
    '/usr/bin/python3',
    'python3',
  ];

  return possiblePaths[0]; // Use venv python from current directory
}

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
    const pythonPath = getPythonPath();
    
    const command = `"${pythonPath}" "${scriptPath}" "${inputPath}" -o "${outputPath}" -r ${emphasisRatio} -m ${minWordLength} -i ${boldIntensity} --json 2>&1`;
    
    console.log('Running command:', command);

    let stdout = '';
    
    try {
      const result = await execAsync(command, { timeout: 300000, maxBuffer: 50 * 1024 * 1024 });
      stdout = result.stdout;
    } catch (execError: any) {
      console.error('Exec error:', execError);
      if (execError.stdout) {
        stdout = execError.stdout;
      } else {
        return NextResponse.json({ 
          success: false, 
          error: `Command failed: ${execError.message}` 
        }, { status: 500 });
      }
    }

    console.log('Python output:', stdout);

    // Clean up input file
    try { await fs.unlink(inputPath); } catch {}

    // Parse result
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

    if (!result) {
      return NextResponse.json({ 
        success: false, 
        error: 'Could not parse Python output: ' + stdout.substring(0, 200) 
      }, { status: 500 });
    }

    if (result.success) {
      try {
        await fs.access(outputPath);
      } catch {
        return NextResponse.json({ 
          success: false, 
          error: 'Output file was not created' 
        }, { status: 500 });
      }

      return NextResponse.json({
        success: true,
        fileId,
        outputPath: `/api/download/${fileId}`,
        fileName: file.name.replace('.pdf', '_bionic.pdf'),
        statistics: result.statistics || {}
      });
    } else {
      return NextResponse.json({ 
        success: false, 
        error: result.error || 'Processing failed' 
      }, { status: 500 });
    }
  } catch (error) {
    console.error('Processing error:', error);
    return NextResponse.json({
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred'
    }, { status: 500 });
  }
}
