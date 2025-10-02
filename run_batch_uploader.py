#!/usr/bin/env python3
"""
Standalone TikTok Batch Uploader Application
"""
import os
import sys
import tkinter as tk
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.absolute()))

from batch_uploader.batch_gui import Dashboard


def main():
    """Main entry point for batch uploader"""
    try:
        root = tk.Tk()
        app = Dashboard(root)
        root.mainloop()
    except Exception as e:
        print(f"Error starting batch uploader: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()