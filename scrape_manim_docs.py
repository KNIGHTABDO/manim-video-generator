#!/usr/bin/env python3
"""
Script to scrape Manim documentation and create a comprehensive reference file.
This will fetch content from key Manim documentation pages and save it for AI reference.
"""

import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime

def scrape_page(url):
    """Scrape content from a single page"""
    try:
        print(f"Fetching: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get main content - try different selectors
        main_content = soup.find('main') or soup.find('div', class_='document') or soup.find('body')
        
        if main_content:
            # Clean up the text
            text = main_content.get_text()
            # Remove excessive whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned_text = '\n'.join(lines)
            return cleaned_text
        else:
            return "Could not extract main content from this page."
            
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return f"Error scraping {url}: {str(e)}"

def main():
    """Main function to scrape all documentation pages"""
    
    # URLs to scrape
    urls = [
        "https://docs.manim.community/en/stable/examples.html",
        "https://docs.manim.community/en/stable/reference_index/animations.html",
        "https://docs.manim.community/en/stable/changelog/0.19.0-changelog.html",
        "https://docs.manim.community/en/stable/reference.html",
        "https://docs.manim.community/en/stable/reference/manim.mobject.text.text_mobject.html",
        "https://docs.manim.community/en/stable/reference/manim.scene.scene.html",
        "https://docs.manim.community/en/stable/reference/manim.animation.html",
        "https://docs.manim.community/en/stable/reference/manim.mobject.geometry.html",
        "https://docs.manim.community/en/stable/reference/manim.utils.color.html",
        "https://docs.manim.community/en/stable/tutorials/quickstart.html"
    ]
    
    # Output file
    output_file = "manim_docs.txt"
    
    print("Starting Manim documentation scraping...")
    print(f"Will save to: {output_file}")
    
    all_content = []
    
    # Add header
    header = f"""
MANIM COMMUNITY DOCUMENTATION REFERENCE
=======================================
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Source: Multiple Manim Community Documentation Pages

This file contains comprehensive Manim documentation for AI reference when generating video scripts.

IMPORTANT NOTES FOR AI USAGE:
- Use only the classes, methods, and patterns shown in this documentation
- Stick to the color constants and animation methods documented here
- Follow the examples and patterns shown for proper Manim code structure
- Pay attention to the changelog for version-specific features

=======================================

"""
    
    all_content.append(header)
    
    # Scrape each URL
    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{len(urls)}] Processing: {url}")
        
        section_header = f"""

{'='*80}
SOURCE: {url}
{'='*80}

"""
        all_content.append(section_header)
        
        content = scrape_page(url)
        all_content.append(content)
        
        # Add delay between requests to be respectful
        time.sleep(2)
        
        print(f"✓ Completed: {len(content)} characters scraped")
    
    # Write all content to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_content))
        
        print(f"\n✅ Successfully saved documentation to: {output_file}")
        print(f"📊 Total file size: {os.path.getsize(output_file)} bytes")
        
        # Show summary
        total_chars = sum(len(content) for content in all_content)
        print(f"📝 Total content: {total_chars:,} characters")
        print(f"📄 URLs processed: {len(urls)}")
        
    except Exception as e:
        print(f"❌ Error saving file: {str(e)}")

if __name__ == "__main__":
    main()
