#!/usr/bin/env python3
"""
ES 50/200 MA Crossover Backtest — Full LEAN Engine-Style Report
Outputs: es_backtest_report.html
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd


# ── Config ─────────────────────────────────────────────────────────────────

@dataclass
class Config:
    host: str; port: int; database: str
    symbol: str; timeframe: str
    fast: int; slow: int
    initial_cash: float


def parse_args() -> Config:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=9000)
    p.add_argument("--database", default="market")
    p.add_argument("--symbol", default="es")
    p.add_argument("--timeframe", default="1d")
    p.add_argument("--fast", type=int, default=50)
    p.add_argument("--slow", type=int, default=200)
    p.add_argument("--initial-cash", type=float, default=100_000.0)
    a = p.parse_args()
    return Config(a.host, a.port, a.database, a.symbol, a.timeframe,
                  a.fast, a.slow, a.initial_cash)


# ── Data ────────────────────────────────────────────────────────────────────

def load_bars(cfg: Config) -> pd.DataFrame:
    from clickhouse_driver import Client
    c = Client(host=cfg.host, port=cfg.port, database=cfg.database)
    rows = c.execute("""
        SELECT mb.timestamp, mb.open, mb.high, mb.low, mb.close, mb.volume
        FROM market_bars mb
        JOIN instruments i ON i.instrument_id = mb.instrument_id
        JOIN timeframes tf  ON tf.timeframe_id = mb.timeframe_id
        WHERE i.symbol = %(sym)s AND tf.label = %(tf)s
        ORDER BY mb.timestamp ASC
    """, {"sym": cfg.symbol, "tf": cfg.timeframe})
    if not rows:
        raise RuntimeError("No data returned from ClickHouse")
    df = pd.DataFrame(rows, columns=["ts","open","high","low","close","volume"])
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    for col in ("open","high","low","close","volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["ts","close"]).drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    return df


# ── Strategy ─────────────────────────────────────────────────────────────────

def run_strategy(df: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    d = df.copy()
    d["fast_ma"] = d["close"].rolling(cfg.fast, min_periods=cfg.fast).mean()
    d["slow_ma"] = d["close"].rolling(cfg.slow, min_periods=cfg.slow).mean()
    d["signal"]  = (d["fast_ma"] > d["slow_ma"]).astype(float)
    d["position"] = d["signal"].shift(1).fillna(0.0)

    d["ret"]      = d["close"].pct_change().fillna(0.0)
    d["strat_ret"] = d["position"] * d["ret"]
    d["equity"]   = cfg.initial_cash * (1 + d["strat_ret"]).cumprod()
    d["bench"]    = cfg.initial_cash * (1 + d["ret"]).cumprod()
    d["peak"]     = d["equity"].cummax()
    d["drawdown"] = (d["equity"] / d["peak"]) - 1.0

    # trade markers
    sig_change = d["position"].diff().fillna(0.0)
    d["entry"] = sig_change == 1.0
    d["exit"]  = sig_change == -1.0
    return d


# ── Statistics ────────────────────────────────────────────────────────────────

def _ann_ret(total: float, n_bars: int, bars_per_year: float = 252.0) -> float:
    yrs = n_bars / bars_per_year
    return (1 + total) ** (1 / yrs) - 1 if yrs > 0 else 0.0

def _sharpe(rets: pd.Series, bars_per_year: float = 252.0) -> float:
    mu = rets.mean(); sig = rets.std(ddof=1)
    return (mu / sig) * math.sqrt(bars_per_year) if sig else 0.0

def _sortino(rets: pd.Series, bars_per_year: float = 252.0) -> float:
    mu = rets.mean()
    down = rets[rets < 0].std(ddof=1)
    return (mu / down) * math.sqrt(bars_per_year) if down else 0.0

def _calmar(cagr: float, max_dd: float) -> float:
    return cagr / abs(max_dd) if max_dd < 0 else 0.0

def compute_stats(d: pd.DataFrame, cfg: Config) -> dict:
    valid = d.dropna(subset=["equity"])
    sr = valid["strat_ret"]; br = valid["ret"]
    total   = valid["equity"].iloc[-1] / cfg.initial_cash - 1
    btotal  = valid["bench"].iloc[-1]  / cfg.initial_cash - 1
    cagr    = _ann_ret(total,  len(valid))
    bcagr   = _ann_ret(btotal, len(valid))
    max_dd  = float(valid["drawdown"].min())
    vol     = float(sr.std(ddof=1) * math.sqrt(252))
    sharpe  = _sharpe(sr)
    sortino = _sortino(sr)
    calmar  = _calmar(cagr, max_dd)
    exposure = float(valid["position"].mean())

    down_rets = sr[sr < 0]
    wins = float(sr[sr > 0].sum())
    losses = float(abs(sr[sr < 0].sum()))
    pf = wins / losses if losses > 0 else 0.0

    entries = int(valid["entry"].sum())
    exits   = int(valid["exit"].sum())

    # longest drawdown duration
    in_dd = valid["drawdown"] < 0
    dd_len = in_dd.astype(int)
    blocks = (dd_len != dd_len.shift()).cumsum()
    max_dd_dur = int(dd_len.groupby(blocks).sum().max()) if in_dd.any() else 0

    return dict(
        start=str(valid["ts"].iloc[0].date()),
        end=str(valid["ts"].iloc[-1].date()),
        data_points=len(d), valid_points=len(valid),
        initial_cash=cfg.initial_cash,
        final_equity=float(valid["equity"].iloc[-1]),
        total_return_pct=total*100, cagr_pct=cagr*100,
        bench_return_pct=btotal*100, bench_cagr_pct=bcagr*100,
        max_dd_pct=max_dd*100, max_dd_dur_days=max_dd_dur,
        vol_pct=vol*100, sharpe=sharpe, sortino=sortino, calmar=calmar,
        exposure_pct=exposure*100, profit_factor=pf,
        win_days_pct=float((sr>0).mean()*100),
        lose_days_pct=float((sr<0).mean()*100),
        entries=entries, exits=exits,
        alpha_pct=(cagr - bcagr)*100,
        fast_ma=cfg.fast, slow_ma=cfg.slow,
    )


# ── Monthly return table ──────────────────────────────────────────────────────

def monthly_returns(d: pd.DataFrame) -> pd.DataFrame:
    valid = d.dropna(subset=["equity"]).copy()
    valid["year"]  = valid["ts"].dt.year
    valid["month"] = valid["ts"].dt.month
    grp = valid.groupby(["year","month"])["strat_ret"].apply(
        lambda x: (1 + x).prod() - 1
    ).unstack(fill_value=np.nan)
    grp.columns = [pd.Timestamp(2000, m, 1).strftime("%b") for m in grp.columns]
    # annual column — use index alignment, no extra (1+) wrapping
    grp["Annual"] = valid.groupby("year")["strat_ret"].apply(
        lambda x: (1 + x).prod() - 1
    )
    return grp


# ── Plots ─────────────────────────────────────────────────────────────────────

COLORS = {"equity":"#2196F3","bench":"#9E9E9E","signal":"#4CAF50",
          "dd":"#F44336","ma_fast":"#FF9800","ma_slow":"#673AB7"}

def _b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor="#1a1a2e", edgecolor="none")
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()

def plot_equity(d: pd.DataFrame, cfg: Config) -> str:
    valid = d.dropna(subset=["equity"])
    fig, ax = plt.subplots(figsize=(14, 4.5), facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.plot(valid["ts"], valid["equity"], color=COLORS["equity"], lw=1.4, label="Strategy")
    ax.plot(valid["ts"], valid["bench"],  color=COLORS["bench"],  lw=1.0, ls="--", alpha=0.7, label="Buy & Hold")
    entries = valid[valid["entry"]]; exits = valid[valid["exit"]]
    ax.scatter(entries["ts"], entries["equity"], marker="^", color="#4CAF50", s=40, zorder=5)
    ax.scatter(exits["ts"],   exits["equity"],   marker="v", color="#F44336", s=40, zorder=5)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x:,.0f}"))
    ax.legend(framealpha=0.3, facecolor="#0f3460", labelcolor="white", fontsize=9)
    ax.set_title(f"{cfg.symbol.upper()} {cfg.fast}/{cfg.slow} MA Crossover — Equity Curve",
                 color="white", fontsize=11, pad=8)
    for spine in ax.spines.values(): spine.set_edgecolor("#333")
    ax.tick_params(colors="#aaa"); ax.yaxis.label.set_color("#aaa"); ax.xaxis.label.set_color("#aaa")
    ax.grid(axis="y", color="#222", lw=0.5)
    return _b64(fig)

def plot_drawdown(d: pd.DataFrame) -> str:
    valid = d.dropna(subset=["equity"])
    fig, ax = plt.subplots(figsize=(14, 2.8), facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.fill_between(valid["ts"], valid["drawdown"]*100, 0,
                    color=COLORS["dd"], alpha=0.55)
    ax.plot(valid["ts"], valid["drawdown"]*100, color=COLORS["dd"], lw=0.8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.1f}%"))
    ax.set_title("Drawdown", color="white", fontsize=10, pad=6)
    for spine in ax.spines.values(): spine.set_edgecolor("#333")
    ax.tick_params(colors="#aaa")
    ax.grid(axis="y", color="#222", lw=0.5)
    return _b64(fig)

def plot_price_with_ma(d: pd.DataFrame, cfg: Config) -> str:
    valid = d.dropna(subset=["fast_ma","slow_ma"])
    # clip to last 5 years for readability
    cutoff = valid["ts"].max() - pd.DateOffset(years=5)
    sub = valid[valid["ts"] >= cutoff]
    fig, ax = plt.subplots(figsize=(14, 4), facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.plot(sub["ts"], sub["close"],    color="#B0BEC5", lw=0.8, label="Close")
    ax.plot(sub["ts"], sub["fast_ma"],  color=COLORS["ma_fast"], lw=1.3, label=f"MA{cfg.fast}")
    ax.plot(sub["ts"], sub["slow_ma"],  color=COLORS["ma_slow"], lw=1.3, label=f"MA{cfg.slow}")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:,.0f}"))
    ax.legend(framealpha=0.3, facecolor="#0f3460", labelcolor="white", fontsize=9)
    ax.set_title("Price + Moving Averages (last 5 years)", color="white", fontsize=10, pad=6)
    for spine in ax.spines.values(): spine.set_edgecolor("#333")
    ax.tick_params(colors="#aaa")
    ax.grid(axis="y", color="#222", lw=0.5)
    return _b64(fig)

def plot_monthly_heatmap(mr: pd.DataFrame) -> str:
    months = [c for c in mr.columns if c != "Annual"]
    heat   = mr[months].copy().astype(float) * 100
    fig, ax = plt.subplots(figsize=(14, max(4, len(heat)*0.32)), facecolor="#1a1a2e")
    ax.set_facecolor("#1a1a2e")
    vmax = max(abs(heat.values[~np.isnan(heat.values)]).max(), 1)
    im = ax.imshow(heat.values, aspect="auto",
                   cmap="RdYlGn", vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(len(months))); ax.set_xticklabels(months, color="#ccc", fontsize=8)
    ax.set_yticks(range(len(heat)));   ax.set_yticklabels(heat.index, color="#ccc", fontsize=8)
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            val = heat.iloc[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                        fontsize=6.5, color="white" if abs(val)>vmax*0.5 else "#333")
    plt.colorbar(im, ax=ax, fraction=0.02, pad=0.01).ax.tick_params(colors="#aaa")
    ax.set_title("Monthly Returns Heatmap (%)", color="white", fontsize=10, pad=8)
    fig.tight_layout()
    return _b64(fig)

def plot_annual_returns(mr: pd.DataFrame) -> str:
    ann = (mr["Annual"] * 100).dropna()
    fig, ax = plt.subplots(figsize=(14, 3), facecolor="#1a1a2e")
    ax.set_facecolor("#16213e")
    colors = ["#4CAF50" if v >= 0 else "#F44336" for v in ann]
    ax.bar(ann.index, ann.values, color=colors, width=0.7)
    ax.axhline(0, color="#666", lw=0.8)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"{x:.0f}%"))
    ax.set_title("Annual Returns", color="white", fontsize=10, pad=6)
    for spine in ax.spines.values(): spine.set_edgecolor("#333")
    ax.tick_params(colors="#aaa")
    ax.grid(axis="y", color="#222", lw=0.5)
    return _b64(fig)


# ── HTML ──────────────────────────────────────────────────────────────────────

def _pct(v: float, dec: int = 2) -> str:
    sign = "+" if v > 0 else ""
    color = "#4CAF50" if v >= 0 else "#F44336"
    return f'<span style="color:{color}">{sign}{v:.{dec}f}%</span>'

def _num(v: float, dec: int = 4) -> str:
    return f"{v:.{dec}f}"

def _dollar(v: float) -> str:
    return f"${v:,.2f}"

def build_html(stats: dict, img_equity: str, img_dd: str, img_price: str,
               img_heatmap: str, img_annual: str, mr: pd.DataFrame) -> str:
    ann = (mr["Annual"] * 100).dropna()
    ann_rows = "".join(
        f'<tr><td>{yr}</td><td class="{"pos" if v>=0 else "neg"}">{v:+.2f}%</td></tr>'
        for yr, v in ann.items()
    )

    def stat_row(label: str, value: str, tooltip: str = "") -> str:
        tip = f' title="{tooltip}"' if tooltip else ""
        return f'<tr><td{tip}>{label}</td><td>{value}</td></tr>'

    strat_rows = "\n".join([
        stat_row("Strategy", f"{stats['fast_ma']}/{stats['slow_ma']} MA Crossover"),
        stat_row("Symbol",   stats["symbol"] if "symbol" in stats else "ES"),
        stat_row("Timeframe", stats.get("timeframe", "1d")),
        stat_row("Start Date", stats["start"]),
        stat_row("End Date",   stats["end"]),
        stat_row("Total Bars (raw)", f"{stats['data_points']:,}"),
        stat_row("Bars (warm-up stripped)", f"{stats['valid_points']:,}"),
    ])

    perf_rows = "\n".join([
        stat_row("Initial Capital",       _dollar(stats["initial_cash"])),
        stat_row("Final Equity",          _dollar(stats["final_equity"])),
        stat_row("Total Net Profit",      _pct(stats["total_return_pct"])),
        stat_row("CAGR",                  _pct(stats["cagr_pct"])),
        stat_row("Benchmark Return (B&H)",_pct(stats["bench_return_pct"])),
        stat_row("Benchmark CAGR",        _pct(stats["bench_cagr_pct"])),
        stat_row("Alpha (annualised)",    _pct(stats["alpha_pct"])),
        stat_row("Max Drawdown",          _pct(stats["max_dd_pct"])),
        stat_row("Max DD Duration (days)",str(stats["max_dd_dur_days"])),
        stat_row("Annual Volatility",     _pct(stats["vol_pct"])),
        stat_row("Sharpe Ratio",          _num(stats["sharpe"])),
        stat_row("Sortino Ratio",         _num(stats["sortino"])),
        stat_row("Calmar Ratio",          _num(stats["calmar"])),
        stat_row("Profit Factor",         _num(stats["profit_factor"])),
        stat_row("Market Exposure",       _pct(stats["exposure_pct"])),
        stat_row("Win Days",              _pct(stats["win_days_pct"])),
        stat_row("Loss Days",             _pct(stats["lose_days_pct"])),
        stat_row("Trade Entries",         str(stats["entries"])),
        stat_row("Trade Exits",           str(stats["exits"])),
    ])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>ES MA Crossover Backtest Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #0d0d1a; color: #cdd; font-family: "Segoe UI", Arial, sans-serif; font-size: 13px; }}
  header {{ background: #0f3460; padding: 18px 32px; border-bottom: 2px solid #1a5276; }}
  header h1 {{ font-size: 20px; color: #e0e0ff; letter-spacing: 1px; }}
  header p  {{ color: #90a; font-size: 11px; margin-top: 4px; }}
  .main {{ padding: 24px 32px; }}
  .section {{ margin-bottom: 28px; }}
  .section h2 {{ color: #8ab4f8; font-size: 13px; letter-spacing: 2px; text-transform: uppercase;
                  border-left: 3px solid #2196F3; padding-left: 10px; margin-bottom: 12px; }}
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 5px 10px; border-bottom: 1px solid #1a1a3a; }}
  tr:hover td {{ background: #11113a; }}
  td:first-child {{ color: #90a4ae; width: 55%; }}
  .pos {{ color: #4CAF50; }}
  .neg {{ color: #F44336; }}
  img.chart {{ width: 100%; border-radius: 6px; border: 1px solid #222; display: block; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 10px;
             background: #1a5276; color: #85c1e9; margin-left: 6px; }}
</style>
</head>
<body>
<header>
  <h1>ES Futures — MA Crossover Backtest Report <span class="badge">{stats['fast_ma']}/{stats['slow_ma']}</span></h1>
  <p>Generated by LEAN Engine Backtest Framework &nbsp;|&nbsp; {stats['start']} → {stats['end']}</p>
</header>
<div class="main">

  <div class="section">
    <h2>Equity Curve</h2>
    <img class="chart" src="data:image/png;base64,{img_equity}">
  </div>

  <div class="section">
    <h2>Drawdown</h2>
    <img class="chart" src="data:image/png;base64,{img_dd}">
  </div>

  <div class="section">
    <h2>Price &amp; Moving Averages</h2>
    <img class="chart" src="data:image/png;base64,{img_price}">
  </div>

  <div class="section grid-2">
    <div>
      <h2>Strategy Info</h2>
      <table>{strat_rows}</table>
    </div>
    <div>
      <h2>Performance Summary</h2>
      <table>{perf_rows}</table>
    </div>
  </div>

  <div class="section">
    <h2>Annual Returns</h2>
    <img class="chart" src="data:image/png;base64,{img_annual}">
  </div>

  <div class="section">
    <h2>Monthly Returns Heatmap</h2>
    <img class="chart" src="data:image/png;base64,{img_heatmap}">
  </div>

  <div class="section">
    <h2>Annual Returns Table</h2>
    <table style="max-width:260px">
      <tr><th style="color:#8ab4f8;text-align:left;padding:5px 10px">Year</th>
          <th style="color:#8ab4f8;text-align:left;padding:5px 10px">Return</th></tr>
      {ann_rows}
    </table>
  </div>

</div>
</body>
</html>"""


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    cfg = parse_args()
    print(f"Loading {cfg.symbol} {cfg.timeframe} bars from ClickHouse...")
    df = load_bars(cfg)
    print(f"  {len(df):,} bars  [{df['ts'].iloc[0].date()} → {df['ts'].iloc[-1].date()}]")

    print(f"Running {cfg.fast}/{cfg.slow} MA crossover strategy...")
    d = run_strategy(df, cfg)

    stats = compute_stats(d, cfg)
    stats["symbol"]    = cfg.symbol
    stats["timeframe"] = cfg.timeframe

    mr = monthly_returns(d)

    print("Building charts...")
    img_equity  = plot_equity(d, cfg)
    img_dd      = plot_drawdown(d)
    img_price   = plot_price_with_ma(d, cfg)
    img_heatmap = plot_monthly_heatmap(mr)
    img_annual  = plot_annual_returns(mr)

    html = build_html(stats, img_equity, img_dd, img_price, img_heatmap, img_annual, mr)

    out = Path.cwd() / "es_backtest_report.html"
    out.write_text(html, encoding="utf-8")

    csv_out = Path.cwd() / "es_ma_crossover_equity_curve.csv"
    d[["ts","close","fast_ma","slow_ma","position","equity","bench","drawdown"]].to_csv(csv_out, index=False)

    json_out = Path.cwd() / "es_ma_crossover_results.json"
    json_out.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print("\n== Backtest Summary ==")
    fields = [
        ("Period",         f"{stats['start']} → {stats['end']}"),
        ("Total Return",   f"{stats['total_return_pct']:+.2f}%"),
        ("CAGR",           f"{stats['cagr_pct']:+.2f}%"),
        ("Benchmark CAGR", f"{stats['bench_cagr_pct']:+.2f}%"),
        ("Alpha",          f"{stats['alpha_pct']:+.2f}%"),
        ("Max Drawdown",   f"{stats['max_dd_pct']:.2f}%"),
        ("Sharpe",         f"{stats['sharpe']:.3f}"),
        ("Sortino",        f"{stats['sortino']:.3f}"),
        ("Calmar",         f"{stats['calmar']:.3f}"),
        ("Profit Factor",  f"{stats['profit_factor']:.3f}"),
        ("Trades",         f"{stats['entries']} entries / {stats['exits']} exits"),
        ("Exposure",       f"{stats['exposure_pct']:.1f}%"),
    ]
    for k, v in fields:
        print(f"  {k:<20} {v}")

    print(f"\nOutputs: {out}\n         {csv_out}\n         {json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
