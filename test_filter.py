#!/usr/bin/env python3
"""
Test script for content filter to verify it blocks coding questions
"""

import os
import sys
from content_filter import ContentFilter

def test_content_filter():
    """Test the content filter with various inputs"""
    
    # Check if Groq API key is available
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("❌ GROQ_API_KEY not found in environment variables")
        print("Please set your Groq API key to test the content filter")
        return
    
    # Initialize content filter
    print("🔧 Initializing content filter...")
    filter_instance = ContentFilter(groq_api_key=groq_api_key, blacklist_threshold=5)
    
    # Test cases that should be BLOCKED
    blocked_tests = [
        "can you provide the python code to compute the number Pi up to its 100th digit?",
        "write a function in JavaScript to sort an array",
        "help me with my math homework",
        "what's the square root of 144?",
        "explain machine learning algorithms",
        "how do I install Python packages?",
        "can you help me debug this code?",
        "write a program that prints hello world"
    ]
    
    # Test cases that should be ALLOWED
    allowed_tests = [
        "what should I discard from this hand?",
        "which tile should I keep in Mahjong?",
        "how do I score a Mahjong hand?",
        "what are the basic rules of American Mahjong?",
        "is this a winning hand in Mahjong?",
        "what's the best strategy for this Mahjong position?",
        "how do I improve my Mahjong gameplay?"
    ]
    
    print("\n🚫 Testing questions that should be BLOCKED:")
    print("=" * 60)
    
    blocked_count = 0
    for i, test_message in enumerate(blocked_tests, 1):
        print(f"\n{i}. Testing: '{test_message[:50]}...'")
        
        try:
            allowed, result = filter_instance.filter_content(test_message, "test_ip")
            
            if not allowed:
                print(f"   ✅ CORRECTLY BLOCKED - {result.reason} (stage: {result.filter_stage})")
                blocked_count += 1
            else:
                print(f"   ❌ INCORRECTLY ALLOWED - {result.reason}")
                
        except Exception as e:
            print(f"   ⚠️  ERROR: {str(e)}")
    
    print(f"\n📊 Blocked {blocked_count}/{len(blocked_tests)} inappropriate questions")
    
    print("\n✅ Testing questions that should be ALLOWED:")
    print("=" * 60)
    
    allowed_count = 0
    for i, test_message in enumerate(allowed_tests, 1):
        print(f"\n{i}. Testing: '{test_message[:50]}...'")
        
        try:
            allowed, result = filter_instance.filter_content(test_message, "test_ip2")
            
            if allowed:
                print(f"   ✅ CORRECTLY ALLOWED - {result.reason}")
                allowed_count += 1
            else:
                print(f"   ❌ INCORRECTLY BLOCKED - {result.reason} (stage: {result.filter_stage})")
                
        except Exception as e:
            print(f"   ⚠️  ERROR: {str(e)}")
    
    print(f"\n📊 Allowed {allowed_count}/{len(allowed_tests)} legitimate Mahjong questions")
    
    # Summary
    print(f"\n🎯 SUMMARY:")
    print(f"   Blocking accuracy: {blocked_count}/{len(blocked_tests)} ({blocked_count/len(blocked_tests)*100:.1f}%)")
    print(f"   Allowing accuracy: {allowed_count}/{len(allowed_tests)} ({allowed_count/len(allowed_tests)*100:.1f}%)")
    
    if blocked_count == len(blocked_tests) and allowed_count == len(allowed_tests):
        print("   🎉 Content filter is working perfectly!")
    elif blocked_count < len(blocked_tests):
        print("   ⚠️  Content filter is not strict enough - some inappropriate questions get through")
    else:
        print("   ⚠️  Content filter may be too strict - some legitimate questions are blocked")

if __name__ == "__main__":
    test_content_filter()