# PyLean Setup Guide

## ✓ Virtual Environment Created

The `pylean` virtual environment has been created and configured with basic Python dependencies.

## Current Setup

- **Python Version**: 3.6.8
- **Virtual Environment**: `/home/rochen/Downloads/pylean/pylean/`
- **Installed Packages**:
  - pandas==1.1.5
  - wrapt==1.12.1
  - quantconnect-stubs (for autocomplete)

## Activating the Environment

### Option 1: Manual Activation
```bash
cd /home/rochen/Downloads/pylean
source pylean/bin/activate
```

### Option 2: Use Helper Script
```bash
cd /home/rochen/Downloads/pylean
source activate_pylean.sh
```

### Deactivating
```bash
deactivate
```

## Testing the Environment

### test_pylean.py

A verification script (`test_pylean.py`) is included to validate the environment setup. This script checks that all required Python packages are properly installed.

**What it tests:**
- ✓ **pandas** installation and version
- ✓ **wrapt** installation and version
- ✓ **matplotlib** installation and version
- ✓ **quantconnect-stubs** installation (checks file system presence)

**Run the test:**
```bash
source pylean/bin/activate
python test_pylean.py
```

**Expected output:**
```
Testing pylean environment setup...

✓ pandas 1.1.5 installed
✓ wrapt 1.12.1 installed
✓ matplotlib 3.3.4 installed
✓ quantconnect-stubs installed (for autocomplete)

============================================================
✓ Environment ready for QuantConnect Lean development!
============================================================

NOTE: To run algorithms locally with Lean, you need:
  1. Build Lean with: dotnet build
  2. Configure Launcher/config.json
  3. Run with: dotnet run --project Launcher

For IDE autocomplete, use: from AlgorithmImports import *
See PYLEAN_SETUP.md for detailed instructions.
```

**What the test does NOT verify:**
- pythonnet/clr-loader (requires Python 3.11+ for full functionality)
- Actual Lean algorithm execution (requires .NET runtime and proper config)
- Network connectivity for data downloads

## Important Notes

### ⚠️ Python Version Limitation

**Current System**: Python 3.6.8
**Lean Requirement**: Python 3.11.11

The virtual environment is currently using Python 3.6.8, which is older than the recommended Python 3.11.11 required by Lean. This means:

1. ✓ You can write and edit Python algorithms
2. ✓ You have autocomplete support via quantconnect-stubs
3. ⚠️ Running algorithms locally may have compatibility issues
4. ⚠️ Some newer Python features won't be available

### To Upgrade Python (Recommended)

To fully use Lean with Python locally, you should install Python 3.11:

#### Using Miniconda (Recommended for Lean):
```bash
# Download and install Miniconda
wget https://cdn.quantconnect.com/miniconda/Miniconda3-py311_24.9.2-0-Linux-x86_64.sh
bash Miniconda3-py311_24.9.2-0-Linux-x86_64.sh -b -p $HOME/miniconda3
rm -rf Miniconda3-py311_24.9.2-0-Linux-x86_64.sh

# Create a new environment with Python 3.11
conda create -n pylean311 python=3.11.11 pandas=2.2.3 wrapt=1.16.0

# Activate it
conda activate pylean311

# Install quantconnect-stubs
pip install quantconnect-stubs

# Set environment variable (add to ~/.bashrc)
export PYTHONNET_PYDLL="$HOME/miniconda3/envs/pylean311/lib/libpython3.11.so"
```

## Using Lean with Python

### 1. Build Lean
```bash
cd /home/rochen/Downloads/pylean
dotnet build
```

### 2. Configure Lean to Run Python Algorithms

Edit `Launcher/config.json`:
```json
{
  "algorithm-type-name": "BasicTemplateAlgorithm",
  "algorithm-language": "Python",
  "algorithm-location": "../../../Algorithm.Python/BasicTemplateAlgorithm.py"
}
```

### 3. Run a Python Algorithm
```bash
cd /home/rochen/Downloads/pylean
dotnet run --project Launcher
```

## Writing Python Algorithms

### Enable Autocomplete

Add this import at the top of your Python algorithm files:
```python
from AlgorithmImports import *
```

### Example Algorithm Location
- Sample algorithms: `Algorithm.Python/`
- Create your own: `Algorithm.Python/MyCustomAlgorithm.py`

### Template Algorithm
```python
from AlgorithmImports import *

class MyAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetEndDate(2020, 12, 31)
        self.SetCash(100000)
        self.AddEquity("SPY", Resolution.Daily)
    
    def OnData(self, data):
        if not self.Portfolio.Invested:
            self.SetHoldings("SPY", 1)
```

## Additional Resources

- [Lean Documentation](https://www.quantconnect.com/docs/)
- [Algorithm.Python README](Algorithm.Python/readme.md)
- [Python API Stubs](https://pypi.org/project/quantconnect-stubs/)
- [Lean CLI](https://www.lean.io/cli)

## Troubleshooting

### SSL Certificate Issues
If you encounter SSL errors when installing packages:
```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org <package-name>
```

### Missing Modules
If quantconnect-stubs causes issues with imports:
```bash
pip uninstall quantconnect-stubs
pip install quantconnect-stubs
```

### PYTHONNET_PYDLL Not Set
For local Lean execution, ensure the environment variable is set:
```bash
export PYTHONNET_PYDLL="/path/to/your/libpython3.11.so"
```
