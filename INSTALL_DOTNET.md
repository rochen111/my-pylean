# Installing .NET SDK on RHEL 8.10

## The Issue

The error "Failed to install packages: Failed to obtain authentication" occurs because the .NET SDK is not installed on your system. The Lean trading engine requires .NET to compile and run.

## Solution: Install .NET SDK

### Option 1: Using DNF Package Manager (Recommended)

```bash
# Enable Microsoft repository
sudo rpm -Uvh https://packages.microsoft.com/config/rhel/8/packages-microsoft-prod.rpm

# Install .NET SDK 8.0 (latest LTS)
sudo dnf install -y dotnet-sdk-8.0

# Verify installation
dotnet --version
```

### Option 2: Using DNF with .NET 6.0 (Alternative)

```bash
# Enable Microsoft repository (if not done above)
sudo rpm -Uvh https://packages.microsoft.com/config/rhel/8/packages-microsoft-prod.rpm

# Install .NET SDK 6.0
sudo dnf install -y dotnet-sdk-6.0

# Verify installation
dotnet --version
```

### Option 3: Manual Installation (If you don't have sudo access)

```bash
# Download .NET SDK installer script
cd ~
wget https://dot.net/v1/dotnet-install.sh
chmod +x dotnet-install.sh

# Install .NET SDK 8.0 to user directory
./dotnet-install.sh --channel 8.0 --install-dir ~/.dotnet

# Add to PATH (add this to ~/.bashrc to make permanent)
export DOTNET_ROOT=$HOME/.dotnet
export PATH=$PATH:$DOTNET_ROOT:$DOTNET_ROOT/tools

# Verify installation
dotnet --version
```

### Option 4: Using Snap (If available)

```bash
sudo snap install dotnet-sdk --classic --channel=8.0
sudo snap alias dotnet-sdk.dotnet dotnet
```

## After Installation

### 1. Verify .NET SDK is installed

```bash
dotnet --version
# Should show: 8.0.xxx or 6.0.xxx
```

### 2. Check .NET info

```bash
dotnet --info
```

### 3. Build Lean

```bash
cd /home/rochen/Downloads/pylean
dotnet build
```

### 4. Run Lean

```bash
dotnet run --project Launcher
```

## Common Issues

### Issue: "command not found: dotnet"

**Solution:** Add dotnet to your PATH:

```bash
# For manual install
echo 'export DOTNET_ROOT=$HOME/.dotnet' >> ~/.bashrc
echo 'export PATH=$PATH:$DOTNET_ROOT:$DOTNET_ROOT/tools' >> ~/.bashrc
source ~/.bashrc
```

### Issue: NuGet authentication errors

**Solution:** Clear NuGet cache and retry:

```bash
dotnet nuget locals all --clear
dotnet restore
dotnet build
```

### Issue: Permission denied errors

**Solution:** You may need to contact your system administrator to install .NET SDK with proper permissions on a corporate RHEL system.

## Checking System Requirements

Lean requires:
- ✓ .NET SDK 6.0 or later (8.0 recommended)
- ✓ Python 3.11 (you have 3.6 - may need upgrade for full functionality)
- ✓ At least 4GB RAM
- ✓ Internet connection for package downloads

## Next Steps

Once .NET SDK is installed:

1. ✓ **Build Lean**: `dotnet build`
2. ✓ **Set Python environment variable** (if using Python 3.11):
   ```bash
   export PYTHONNET_PYDLL="$HOME/miniconda3/envs/pylean311/lib/libpython3.11.so"
   ```
3. ✓ **Configure algorithm**: Edit `Launcher/config.json`
4. ✓ **Run backtest**: `dotnet run --project Launcher`

## Need Help?

If you encounter permission issues or cannot install .NET SDK:
- Contact your system administrator
- Use the manual installation method to user directory
- Consider using Docker container with Lean pre-installed

## Lean with Docker (Alternative Approach)

If you cannot install .NET SDK, you can run Lean in Docker:

```bash
# Pull Lean Docker image
docker pull quantconnect/lean

# Run Lean algorithm
docker run -v /home/rochen/Downloads/pylean:/Lean quantconnect/lean
```

This bypasses the need for local .NET SDK installation.
