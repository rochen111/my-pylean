#!/usr/bin/env python3
"""
Test script to verify pylean environment setup
This tests that the quantconnect-stubs package is properly installed
for IDE autocomplete support.
"""

def test_imports():
    """Test basic imports"""
    print("Testing pylean environment setup...")
    print()
    
    # Check pandas
    try:
        import pandas as pd
        print(f"✓ pandas {pd.__version__} installed")
    except ImportError:
        print("✗ pandas not installed")
        return False
    
    # Check wrapt
    try:
        import wrapt
        print(f"✓ wrapt {wrapt.__version__} installed")
    except ImportError:
        print("✗ wrapt not installed")
        return False
    
    # Check matplotlib (from quantconnect-stubs dependencies)
    try:
        import matplotlib
        print(f"✓ matplotlib {matplotlib.__version__} installed")
    except ImportError:
        print("✗ matplotlib not installed")
        return False
    
    # Check QuantConnect stubs (they're installed but need pythonnet/clr to fully work)
    try:
        import os
        qc_path = os.path.join(os.getcwd(), 'pylean', 'lib', 'python3.6', 'site-packages', 'QuantConnect')
        if os.path.exists(qc_path):
            print(f"✓ quantconnect-stubs installed (for autocomplete)")
        else:
            print("✗ quantconnect-stubs not found")
            return False
    except Exception as e:
        print(f"✗ Error checking quantconnect-stubs: {e}")
        return False
    
    print()
    print("="*60)
    print("✓ Environment ready for QuantConnect Lean development!")
    print("="*60)
    print()
    print("NOTE: To run algorithms locally with Lean, you need:")
    print("  1. Build Lean with: dotnet build")
    print("  2. Configure Launcher/config.json")
    print("  3. Run with: dotnet run --project Launcher")
    print()
    print("For IDE autocomplete, use: from AlgorithmImports import *")
    print("See PYLEAN_SETUP.md for detailed instructions.")
    
    return True

if __name__ == "__main__":
    test_imports()
