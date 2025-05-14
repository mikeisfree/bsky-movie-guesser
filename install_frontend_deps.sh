#!/bin/bash

echo "Installing frontend dependencies..."
pip install -r frontend/requirements.txt

# Check if pydantic-settings was installed
if python -c "import pydantic_settings" 2>/dev/null; then
    echo "✅ Dependencies installed successfully."
else
    echo "❌ Failed to install pydantic-settings."
    echo "Try manually running: pip install pydantic-settings>=2.0.0"
fi

echo "You can now run the frontend with: python run_frontend.py"
