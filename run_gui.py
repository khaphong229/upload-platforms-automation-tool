#!/usr/bin/env python3
"""
Simple launcher script for the GUI version of the Content Distribution Tool
"""
import sys
import os
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

try:
    from gui_main import main
    
    if __name__ == "__main__":
        print("Starting Auto Content Distribution Tool GUI...")
        main()
        
except ImportError as e:
    print(f"Error importing GUI modules: {e}")
    print("Please make sure all dependencies are installed:")
    print("pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"Error starting GUI: {e}")
    sys.exit(1)
