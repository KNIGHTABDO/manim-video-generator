#!/usr/bin/env python3

"""Quick test script for AI generation improvements"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import generate_manim_code

def test_generation():
    """Test the improved AI generation system"""
    concept = 'solve for x ; x^2 + 3 = 0'
    
    print(f"Testing AI generation for: {concept}")
    print("=" * 60)
    
    try:
        result = generate_manim_code(concept)
        
        print(f"Generated code length: {len(result)} characters")
        print("\n=== SYNTAX CHECK ===")
        
        try:
            compile(result, '<test>', 'exec')
            print("✅ Syntax validation: PASSED")
        except SyntaxError as e:
            print(f"❌ Syntax validation: FAILED - {e}")
            return False
        
        print("\n=== CODE QUALITY CHECKS ===")
        
        # Check for common issues
        issues = []
        if '[' in result and '.set_color()' in result:
            issues.append("❌ Contains dangerous MathTex indexing")
        
        if result.count('(') != result.count(')'):
            issues.append("❌ Unmatched parentheses")
            
        if result.count('{') != result.count('}'):
            issues.append("❌ Unmatched braces")
            
        if result.count('[') != result.count(']'):
            issues.append("❌ Unmatched brackets")
            
        if 'class MainScene' not in result and 'class ' not in result:
            issues.append("❌ Missing proper scene class")
            
        if 'def construct' not in result:
            issues.append("❌ Missing construct method")
            
        if len(result) < 1000:
            issues.append("❌ Generated code too short (< 1000 chars)")
            
        if issues:
            print("\n".join(issues))
            return False
        else:
            print("✅ All quality checks passed")
        
        print("\n=== FIRST 300 CHARACTERS ===")
        print(result[:300])
        
        print("\n=== LAST 300 CHARACTERS ===")
        print(result[-300:])
        
        return True
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_generation()
    print(f"\n{'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
