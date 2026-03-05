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
    
    // Run Python script and capture both stdout and stderr
    const command = `python3 "${scriptPath}" "${inputPath}" -o "${outputPath}" -r ${emphasisRatio} -m ${minWordLength} -i ${boldIntensity} --json 2>&1`;
    
    console.log('Running command:', command);

    let stdout = '';
    let stderr = '';
    
    try {
      const result = await execAsync(command, { timeout: 300000, maxBuffer: 50 * 1024 * 1024 });
      stdout = result.stdout;
      stderr = result.stderr;
    } catch (execError: any) {
      console.error('Exec error:', execError);
      // Try to parse error from stdout
      if (execError.stdout) {
        try {
          const errorResult = JSON.parse(execError.stdout);
          if (errorResult.error) {
            return NextResponse.json({ 
              success: false, 
              error: `Python error: ${errorResult.error}` 
            }, { status: 500 });
          }
        } catch {
          // Not JSON, return raw error
          return NextResponse.json({ 
            success: false, 
            error: `Command failed: ${execError.stdout || execError.message}` 
          }, { status: 500 });
        }
      }
      return NextResponse.json({ 
        success: false, 
        error: `Command failed: ${execError.message}` 
      }, { status: 500 });
    }

    console.log('Python stdout:', stdout);
    console.log('Python stderr:', stderr);

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
      } catch {
        // Not JSON, continue
      }
    }

    if (!result) {
      result = { success: true, output_path: outputPath };
    }

    if (result.success) {
      // Verify output file exists
      try {
        await fs.access(outputPath);
      } catch {
        return NextResponse.json({ 
          success: false, 
          error: 'Output file was not created. Check if Python dependencies are installed: pip install pdfplumber reportlab pypdf' 
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
