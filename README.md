# Bionic Reading PDF Converter - Web UI

A beautiful web interface for converting PDFs with bionic reading enhancement.

## Prerequisites

- **Node.js 18+**
- **Python 3.8+**
- pip

## Quick Start

### 1. Install Node.js Dependencies

```bash
npm install
# or
yarn install
# or  
pnpm install
```

### 2. Install Python Dependencies

```bash
cd scripts
pip install -r requirements.txt
# On Debian/Ubuntu, you may need:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the Development Server

```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Features

- 🎨 Beautiful, accessible UI
- 📤 Drag-and-drop PDF upload
- ⚙️ Customizable settings (emphasis ratio, intensity, word length)
- 👁️ Live preview of bionic transformation
- 📊 Processing statistics
- ⬇️ Easy download of enhanced PDFs

## Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| Emphasis Ratio | Percentage of word to bold | 40% |
| Min Word Length | Skip words shorter than this | 3 |
| Bold Intensity | Light/Medium/Heavy | Medium |
| Preserve Layout | Keep original formatting | Yes |

## Project Structure

```
├── src/
│   ├── app/
│   │   ├── page.tsx          # Main UI
│   │   ├── layout.tsx        # Root layout
│   │   ├── globals.css       # Styles
│   │   └── api/              # API routes
│   │       ├── process/      # PDF processing
│   │       ├── preview/      # Text preview
│   │       └── download/     # File download
│   ├── components/ui/        # UI components
│   └── lib/utils.ts          # Utilities
├── scripts/                   # Python backend
│   ├── process_pdf.py
│   ├── bionic_reader.py
│   ├── pdf_extractor.py
│   └── pdf_generator.py
└── package.json
```

## Tech Stack

- **Frontend**: Next.js 14, React 18, Tailwind CSS
- **UI Components**: Radix UI, shadcn/ui style
- **Backend**: Next.js API Routes
- **PDF Processing**: Python (pdfplumber, reportlab, pypdf)

## License

MIT
