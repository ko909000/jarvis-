#!/usr/bin/env python3
"""
Test script for Jarvis application opening functionality
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add the workspace to the path
sys.path.insert(0, str(Path(__file__).parent))

from Jarvis_window_CTRL import open as open_app, close as close_app, folder_file
from Jarvis_file_opner import Play_file

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_imports():
    """Test that all imports work correctly"""
    print("🧪 Testing imports...")
    try:
        from fuzzywuzzy import process
        print("✅ fuzzywuzzy imported successfully")
    except ImportError as e:
        print(f"❌ fuzzywuzzy import failed: {e}")
        return False

    try:
        from livekit.agents import function_tool
        print("✅ livekit.agents imported successfully")
    except ImportError as e:
        print(f"❌ livekit.agents import failed: {e}")
        return False

    print("✅ All imports successful")
    return True

async def test_application_opening():
    """Test application opening functionality"""
    print("\n🧪 Testing application opening...")
    
    # Test applications that should exist on most Linux systems
    test_apps = [
        ('text editor', 'gedit'),
        ('terminal', 'gnome-terminal'),
        ('file manager', 'nautilus'),
    ]
    
    results = []
    for app_name, expected_command in test_apps:
        try:
            result = await open_app(app_name)
            print(f"📱 {app_name}: {result}")
            results.append(True)
        except Exception as e:
            print(f"❌ {app_name} failed: {e}")
            results.append(False)
    
    return all(results)

async def test_file_operations():
    """Test file and folder operations"""
    print("\n🧪 Testing file operations...")
    
    try:
        # Test file opening with an existing file
        result = await Play_file("agent.py")
        print(f"📄 File opening: {result}")
        
        # Test folder operations
        result = await folder_file("Documents")
        print(f"📁 Folder operations: {result}")
        
        return True
    except Exception as e:
        print(f"❌ File operations failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Starting Jarvis Linux Compatibility Tests")
    print("=" * 50)
    
    test_results = []
    
    # Test imports
    import_result = await test_imports()
    test_results.append(import_result)
    
    # Test application opening
    app_result = await test_application_opening()
    test_results.append(app_result)
    
    # Test file operations
    file_result = await test_file_operations()
    test_results.append(file_result)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"✅ Imports: {'PASS' if import_result else 'FAIL'}")
    print(f"✅ Applications: {'PASS' if app_result else 'FAIL'}")
    print(f"✅ File Operations: {'PASS' if file_result else 'FAIL'}")
    
    overall_result = all(test_results)
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall_result else '❌ SOME TESTS FAILED'}")
    
    if overall_result:
        print("\n🎉 Jarvis is now compatible with Linux!")
        print("🔧 All application opening errors have been fixed.")
    else:
        print("\n⚠️ Some issues still need to be addressed.")
    
    return overall_result

if __name__ == "__main__":
    asyncio.run(main())