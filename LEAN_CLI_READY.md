# Lean CLI Setup Complete!

## ✅ What's Installed

- **Python 3.9.20** in pylean venv
- **Lean CLI 1.0.221**
- **pandas 2.3.3**
- **wrapt 2.0.1**
- **quantconnect-stubs 17485**

## 🚀 Quick Start

### Option 1: Use the Wrapper Script (Recommended)

```bash
cd /home/rochen/Downloads/pylean
./lean-cli.sh --help
./lean-cli.sh init my-project
```

The wrapper script handles SSL certificate issues automatically.

### Option 2: Manual Activation

```bash
cd /home/rochen/Downloads/pylean
source pylean/bin/activate

# Set environment variables for SSL
export PYTHONHTTPSVERIFY=0
export REQUESTS_CA_BUNDLE=""

# Use lean commands
lean --help
lean init my-project
```

## 📝 Common Lean CLI Commands

```bash
# Initialize a new project
./lean-cli.sh init my-project

# Create a new algorithm
./lean-cli.sh create-project --language python my-algorithm

# Run a backtest (requires Docker)
./lean-cli.sh backtest my-project

# Download data
./lean-cli.sh data download

# Cloud commands
./lean-cli.sh cloud login
./lean-cli.sh cloud push my-project
./lean-cli.sh cloud backtest my-project
```

## 🐳 Note About Docker

Lean CLI uses Docker to run backtests locally. If you don't have Docker:

1. **Use cloud backtesting**: Upload your algorithms to QuantConnect
2. **Request Docker access**: Ask your system admin to install Docker
3. **Write algorithms locally**: Develop with autocomplete, backtest in the cloud
4. **Prefer cloud backtesting on low-memory hosts**: Local Docker backtests can fail when RAM is limited

## 📂 Your Algorithm is Ready

The **ESFuturesRiskManagementDemo.py** algorithm is ready to use:

```bash
# Copy to a Lean CLI project
./lean-cli.sh init es-futures-demo
cp Algorithm.Python/ESFuturesRiskManagementDemo.py ~/es-futures-demo/

# Or push to QuantConnect cloud
./lean-cli.sh cloud login
./lean-cli.sh cloud push es-futures-demo
```

## 🔧 Troubleshooting

### SSL Certificate Errors

Already handled by `lean-cli.sh`. If you see SSL errors with manual commands, set:
```bash
export PYTHONHTTPSVERIFY=0
export REQUESTS_CA_BUNDLE=""
```

### Docker Not Available

Use cloud backtesting instead:
```bash
./lean-cli.sh cloud login
./lean-cli.sh cloud backtest my-project
```

### Debian 12 OOM: `Killed process ... (clickhouse-serv)`

If you see kernel messages like:
`Out of memory: Killed process ... (clickhouse-serv)`, your host is running out of RAM during local Docker backtests.

Use one or more of these mitigations:

1. **Best quick fix:** run backtests in QuantConnect cloud instead of local Docker:
   ```bash
   ./lean-cli.sh cloud backtest my-project
   ```
2. **Add swap on Debian 12** (helps prevent OOM kills):
   ```bash
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```
3. **Reduce memory pressure:** stop other memory-heavy containers/processes before running `lean backtest`.

### Python Version Issues

Your venv is now using Python 3.9.20 which is fully compatible with Lean CLI.

## 📚 Resources

- **Lean CLI Docs**: https://www.lean.io/docs/v2/lean-cli/getting-started/lean-cli
- **QuantConnect Docs**: https://www.quantconnect.com/docs/
- **Cloud Platform**: https://www.quantconnect.com/

## 🎯 Next Steps

1. **Test Lean CLI**: `./lean-cli.sh --version`
2. **Create a project**: `./lean-cli.sh init my-first-project`
3. **Write your algorithm**: Edit the Python files with full autocomplete
4. **Backtest**: Use Docker locally or QuantConnect cloud

Your development environment is now fully configured! 🎉
