#!/usr/bin/env python3
"""
Simple script to update Manim documentation reference.
Run this whenever you want to refresh the documentation.
"""

import subprocess
import os

def update_docs():
    """Update the Manim documentation reference file"""
    script_path = os.path.join(os.path.dirname(__file__), 'scrape_manim_docs.py')
    
    if os.path.exists(script_path):
        print("Updating Manim documentation...")
        try:
            result = subprocess.run(['py', script_path], 
                                  capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            if result.returncode == 0:
                print("✅ Documentation updated successfully!")
                print(result.stdout)
            else:
                print("❌ Error updating documentation:")
                print(result.stderr)
        except Exception as e:
            print(f"❌ Error running update script: {str(e)}")
    else:
        print("❌ Documentation scraper not found!")

if __name__ == "__main__":
    update_docs()
