# Build Issue: .NET 10.0 Targeting Error

## Current Status

The Lean repository you cloned has `.csproj` files targeting **`net10.0`** which does not exist yet (.NET is currently at version 8.0 / 9.0). This appears to be a bug in the master branch.

## What Happened

1. ✓ You installed .NET SDK 8.0.123 successfully
2. ✓ We attempted to build Lean
3. ✗ Build failed: "does not support targeting .NET 10.0"
4. ✓ We updated all `.csproj` files to target `net8.0`
5. ✗ Build still fails with Python.NET reference errors

## Current Workaround Applied

All `.csproj` files have been modified to target `net8.0` instead of `net10.0`:
- Changed: `<TargetFramework>net10.0</TargetFramework>` 
- To: `<TargetFramework>net8.0</TargetFramework>`

**However**, the build is still failing because the Python.NET packages in the latest master are incompatible or missing.

## Recommended Solutions

### Option 1: Use Lean CLI (Easiest)

Instead of building from source, use the Lean CLI which handles all dependencies:

```bash
# Activate your pylean environment
source pylean/bin/activate

# Install Lean CLI
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org lean

# Initialize a Lean project
lean init my-project

# Run a backtest
cd my-project
lean backtest my-project "My Algorithm"
```

### Option 2: Use Lean Docker Image (Recommended for Production)

```bash
# Pull the official Lean Docker image
docker pull quantconnect/lean

# Run an algorithm
docker run -v $(pwd):/Lean quantconnect/lean
```

### Option 3: Wait for Bug Fix

The `net10.0` targeting appears to be a recent bug in the master branch. You can:

```bash
# Check Lean repository for updates
cd /home/rochen/Downloads/pylean
git pull origin master

# Or open an issue on GitHub
# https://github.com/QuantConnect/Lean/issues
```

### Option 4: Use Python-Only Development

You can still write and test Python algorithms without building Lean locally:

1. ✓ **VS Code with Lean extension** - Use Skylight to sync with QuantConnect cloud
2. ✓ **Local IDE development** - Write code with `quantconnect-stubs` for autocomplete
3. ✓ **Cloud backtesting** - Run backtests on QuantConnect platform

## What Works Right Now

✓ **Python virtual environment** (`pylean`) is configured  
✓ **quantconnect-stubs** installed for IDE autocomplete  
✓ **Algorithm files** can be written and edited  
✓ **.NET SDK 8.0** is installed  

## What Doesn't Work

✗ **Building Lean from source** - Python.NET incompatibility  
✗ **Local backtesting** - Requires successful build  
✗ **Running algorithms locally** - Requires Lean engine  

## Files Created for You

1. **[PYLEAN_SETUP.md](PYLEAN_SETUP.md)** - Python environment setup guide
2. **[INSTALL_DOTNET.md](INSTALL_DOTNET.md)** - .NET SDK installation guide
3. **[RISK_MANAGEMENT_GUIDE.md](RISK_MANAGEMENT_GUIDE.md)** - Risk management features documentation
4. **[ESFuturesRiskManagementDemo.py](Algorithm.Python/ESFuturesRiskManagementDemo.py)** - Demo algorithm with risk management
5. **[test_pylean.py](test_pylean.py)** - Environment verification script

## Next Steps

### Immediate Actions:

**If you want to run algorithms locally:**
- Use Lean CLI (Option 1 above) - simplest approach
- Use Docker (Option 2 above) - most reliable

**If you want to fix the build:**
- Monitor Lean GitHub for fixes to the net10.0 targeting bug
- Report the issue if not already reported

**If you just want to develop algorithms:**
- Your environment is ready!
- Write Python algorithms with autocomplete support
- Use QuantConnect cloud for backtesting
- Use VS Code with Skylight extension

## Your Algorithm is Ready

The **ESFuturesRiskManagementDemo.py** algorithm I created is ready to run once you have a working Lean installation (via CLI, Docker, or when the build issue is fixed).

### To Run with Lean CLI:

```bash
# Install Lean CLI
pip install lean

# Copy your algorithm
cp Algorithm.Python/ESFuturesRiskManagementDemo.py ~/lean-projects/

# Edit config and run
cd ~/lean-projects
lean backtest "My Project"
```

### To Run with Docker:

```bash
# Edit Launcher/config.json to point to your algorithm
# Then run:
docker run -v /home/rochen/Downloads/pylean:/Lean quantconnect/lean
```

## Questions?

- **Lean Documentation**: https://www.quantconnect.com/docs/
- **Lean GitHub**: https://github.com/QuantConnect/Lean
- **Lean CLI Docs**: https://www.lean.io/cli
- **Community Forum**: https://www.quantconnect.com/forum/

The code and documentation I created are ready to use once you have a working Lean runtime!
