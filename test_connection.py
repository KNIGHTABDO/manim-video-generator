#!/usr/bin/env python3
"""
Simple connection test for ngrok
"""

import requests
import json

def test_ngrok_connection():
    """Test connection to ngrok URL"""
    
    ngrok_url = "https://1f002d68968a.ngrok-free.app"
    
    print(f"🔍 Testing connection to: {ngrok_url}")
    
    try:
        # Test with ngrok skip header
        headers = {
            'ngrok-skip-browser-warning': 'true',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        print("📡 Making request with headers...")
        response = requests.get(ngrok_url, headers=headers, timeout=10)
        
        print(f"✅ Status Code: {response.status_code}")
        print(f"✅ Response Headers: {dict(response.headers)}")
        print(f"✅ Content Length: {len(response.content)} bytes")
        
        if response.status_code == 200:
            print("🎉 Connection successful!")
            return True
        else:
            print(f"⚠️ Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection Error: {str(e)}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"❌ Timeout Error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_ngrok_connection()
