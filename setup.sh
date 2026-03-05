#!/bin/bash
set -e

echo "🚀 Setting up Bionic Reading PDF Converter..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Install it first."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install --upgrade pip
pip install pdfplumber reportlab pypdf Pillow

# Verify installation
echo ""
echo "🔍 Verifying installation..."
python3 -c "import pdfplumber; import reportlab; import pypdf; print('✅ Python dependencies installed!')"

# Install Node dependencies if package.json exists
if [ -f "package.json" ]; then
    echo ""
    echo "📥 Installing Node.js dependencies..."
    npm install
    echo "✅ Node.js dependencies installed!"
fi

echo ""
echo "═══════════════════════════════════════════════"
echo "✅ Setup complete!"
echo ""
echo "To run the app:"
echo "  1. source venv/bin/activate"
echo "  2. npm run dev"
echo ""
echo "Then open: http://localhost:3000"
echo "═══════════════════════════════════════════════"
