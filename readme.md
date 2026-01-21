# My PyLean

Custom financial data analysis and charting tools built on the LEAN framework.

## Source Repository

This project is based on [QuantConnect LEAN](https://github.com/QuantConnect/Lean) - an open-source algorithmic trading engine.

Original repository: https://github.com/QuantConnect/Lean

## Custom Code

### ES Futures Data Analysis (`get_es_futures_actual_data.py`)

Python script for downloading and analyzing S&P 500 / ES Futures market data:

- **Data Source**: Federal Reserve Economic Data (FRED) API
- **Date Range**: 2016-2026 (2,514 trading days)
- **Features**:
  - OHLC bar chart visualization
  - Technical indicators: SMA (20/50/200), EMA (20/50), Bollinger Bands, ATR(10)
  - Automated peak and bottom detection using scipy
  - Exports processed data with indicators to CSV
  - Generates annotated price charts with marked peaks/bottoms

**Usage**:
```bash
source pylean/bin/activate
python get_es_futures_actual_data.py
```

**Output**:
- `es_futures_actual_data.csv` - Full dataset with indicators
- `es_futures_actual_3months.png` - Annotated chart with technical analysis

### Data Files

- `es_futures_actual_data.csv` - Processed S&P 500 data with technical indicators
- `sp500_futures_historical.csv` - Raw FRED download cache

## Installation

### Python Environment

```bash
python -m venv pylean
source pylean/bin/activate  # Linux/Mac
pip install pandas numpy matplotlib scipy requests beautifulsoup4
```

### Dependencies

- pandas - Data manipulation
- numpy - Numerical computing
- matplotlib - Chart generation
- scipy - Peak/bottom detection
- requests - HTTP downloads

## Repository Cleanup

This repository has been optimized from the original LEAN codebase:
- Removed sample data (225MB)
- Removed test suites (26MB)
- Removed build artifacts
- Kept core LEAN framework for future algorithmic trading development

---

**Original LEAN Framework**: https://github.com/QuantConnect/Lean  
**Documentation**: https://www.lean.io/docs/
