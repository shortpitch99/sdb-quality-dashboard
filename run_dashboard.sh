#!/bin/bash
# Quality Report Dashboard Runner

echo "🔧 Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Dependencies installed"

echo "📊 Starting Quality Report Dashboard..."
echo "🌐 Dashboard will open in your browser at http://localhost:8501"
echo "🔄 Press Ctrl+C to stop the dashboard"
echo ""

streamlit run streamlit_app.py
