#!/usr/bin/env python3
"""Interactive market-condition chart viewer for FRED-style CSV files.

Reads a CSV with at least: timestamp, close
Computes SMA5/20/50/200 and highlights rows where:
close < sma5 < sma20 < sma50 and sma50 > sma200

Outputs:
- Interactive HTML chart
- CSV of matching condition rows
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {"timestamp", "close"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive chart for SMA hierarchy conditions")
    parser.add_argument(
        "--csv",
        default="djia_daily_max_fred_data.csv",
        help="Input CSV path (default: djia_daily_max_fred_data.csv)",
    )
    parser.add_argument(
        "--out-html",
        default="djia_market_conditions.html",
        help="Output HTML chart path",
    )
    parser.add_argument(
        "--out-conditions",
        default="djia_condition_matches.csv",
        help="Output CSV for condition matches",
    )
    parser.add_argument(
        "--out-occurrences",
        default="djia_condition_occurrences.csv",
        help="Output CSV for grouped condition occurrences",
    )
    parser.add_argument(
        "--gap-days",
        type=int,
        default=3,
        help="Max calendar-day gap allowed within one occurrence block (default: 3)",
    )
    parser.add_argument(
        "--context-days",
        type=int,
        default=20,
        help="Days of context to show before and after each occurrence (default: 20)",
    )
    return parser.parse_args()


def load_data(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["timestamp", "close"]).sort_values("timestamp").reset_index(drop=True)

    for window in (5, 20, 50, 200):
        df[f"sma{window}"] = df["close"].rolling(window=window, min_periods=window).mean()

    df["condition"] = (
        (df["close"] < df["sma5"])
        & (df["sma5"] < df["sma20"])
        & (df["sma20"] < df["sma50"])
        & (df["sma50"] > df["sma200"])
        & (df["close"] > df["sma200"])
        & (df["sma20"] > df["sma200"])
    )

    return df


def build_occurrences(hits: pd.DataFrame, gap_days: int) -> pd.DataFrame:
    if hits.empty:
        return pd.DataFrame(columns=["occurrence_id", "start", "end", "days"])

    blocks = hits[["timestamp"]].sort_values("timestamp").copy()
    blocks["gap_days"] = blocks["timestamp"].diff().dt.days
    blocks["new_block"] = blocks["gap_days"].isna() | (blocks["gap_days"] > gap_days)
    blocks["occurrence_id"] = blocks["new_block"].cumsum().astype(int)

    grouped = (
        blocks.groupby("occurrence_id", as_index=False)
        .agg(start=("timestamp", "min"), end=("timestamp", "max"), days=("timestamp", "count"))
        .sort_values("start")
        .reset_index(drop=True)
    )
    return grouped


def build_chart(
    df: pd.DataFrame,
    occurrences: pd.DataFrame,
    html_path: Path,
    context_days: int,
) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise RuntimeError(
            "plotly is required for interactive charts. Install with: pip install plotly"
        ) from exc

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["close"],
            mode="lines",
            name="Close",
            line={"width": 3.5, "color": "#111111"},
        )
    )

    for sma_name, color in [
        ("sma5", "#4e79a7"),
        ("sma20", "#f28e2b"),
        ("sma50", "#59a14f"),
        ("sma200", "#e15759"),
    ]:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df[sma_name],
                mode="lines",
                name=sma_name.upper(),
                line={"width": 1.4, "color": color},
            )
        )

    hits = df[df["condition"]]
    if not hits.empty:
        fig.add_trace(
            go.Scatter(
                x=hits["timestamp"],
                y=hits["close"],
                mode="markers",
                name="Condition Match",
                marker={"size": 7, "color": "#b07aa1", "symbol": "diamond"},
                hovertemplate=(
                    "<b>%{x|%Y-%m-%d}</b><br>"
                    "Close: %{y:.2f}<br>"
                    "SMA5<SMA20<SMA50 and Close<SMA5<br>"
                    "SMA50>SMA200<extra></extra>"
                ),
            )
        )

    for _, row in occurrences.iterrows():
        fig.add_vrect(
            x0=row["start"],
            x1=row["end"],
            fillcolor="#b07aa1",
            opacity=0.08,
            line_width=0,
            layer="below",
        )

    price_cols = ["close", "sma5", "sma20", "sma50", "sma200"]
    full_min = df[price_cols].min(skipna=True).min()
    full_max = df[price_cols].max(skipna=True).max()
    full_pad = (full_max - full_min) * 0.05 if full_max > full_min else max(full_max * 0.01, 1.0)

    zoom_buttons = [
        {
            "label": "All",
            "method": "relayout",
            "args": [
                {
                    "xaxis.range": [df["timestamp"].min(), df["timestamp"].max()],
                    "yaxis.range": [full_min - full_pad, full_max + full_pad],
                }
            ],
        }
    ]

    pad = pd.Timedelta(days=context_days)
    for _, row in occurrences.iterrows():
        occ_mask = (df["timestamp"] >= (row["start"] - pad)) & (df["timestamp"] <= (row["end"] + pad))
        occ_slice = df.loc[occ_mask, price_cols]
        occ_min = occ_slice.min(skipna=True).min()
        occ_max = occ_slice.max(skipna=True).max()

        if pd.isna(occ_min) or pd.isna(occ_max):
            occ_min, occ_max = full_min, full_max

        occ_pad = (occ_max - occ_min) * 0.2 if occ_max > occ_min else max(occ_max * 0.01, 1.0)

        zoom_buttons.append(
            {
                "label": f"Occ {int(row['occurrence_id'])} ({int(row['days'])}d, ctx {context_days}d)",
                "method": "relayout",
                "args": [
                    {
                        "xaxis.range": [row["start"] - pad, row["end"] + pad],
                        "yaxis.range": [occ_min - occ_pad, occ_max + occ_pad],
                    }
                ],
            }
        )

    fig.update_layout(
        title="Price and SMA Hierarchy Condition Explorer",
        template="plotly_white",
        hovermode="x unified",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        updatemenus=[
            {
                "buttons": zoom_buttons,
                "direction": "down",
                "showactive": False,
                "x": 1.0,
                "xanchor": "right",
                "y": 1.22,
                "yanchor": "top",
                "pad": {"r": 0, "t": 0},
            }
        ],
        annotations=[
            {
                "text": "Jump to occurrence",
                "x": 1.0,
                "xref": "paper",
                "y": 1.255,
                "yref": "paper",
                "xanchor": "right",
                "yanchor": "top",
                "showarrow": False,
                "font": {"size": 12},
            }
        ],
        xaxis={
            "title": "Date",
            "range": [df["timestamp"].min(), df["timestamp"].max()],
            "rangeslider": {"visible": True},
            "rangeselector": {
                "buttons": [
                    {"count": 1, "label": "1m", "step": "month", "stepmode": "backward"},
                    {"count": 3, "label": "3m", "step": "month", "stepmode": "backward"},
                    {"count": 6, "label": "6m", "step": "month", "stepmode": "backward"},
                    {"count": 1, "label": "1y", "step": "year", "stepmode": "backward"},
                    {"step": "all", "label": "All"},
                ]
            },
        },
        yaxis={"title": "Price", "range": [full_min - full_pad, full_max + full_pad]},
    )

    post_script = """
(function() {
    const gd = document.getElementById('market-condition-chart');
    if (!gd || !window.Plotly) return;

    const controls = document.createElement('div');
    controls.style.display = 'flex';
    controls.style.gap = '8px';
    controls.style.flexWrap = 'wrap';
    controls.style.alignItems = 'center';
    controls.style.margin = '0 0 10px 0';
    controls.style.fontFamily = 'sans-serif';

    const label = document.createElement('span');
    label.textContent = 'Chart controls:';
    label.style.fontWeight = '600';
    controls.appendChild(label);

    function zoomOut() {
        const xAxis = gd._fullLayout && gd._fullLayout.xaxis ? gd._fullLayout.xaxis : gd.layout.xaxis;
        const yAxis = gd._fullLayout && gd._fullLayout.yaxis ? gd._fullLayout.yaxis : gd.layout.yaxis;
        if (!xAxis || !xAxis.range || xAxis.range.length < 2) return;
        if (!yAxis || !yAxis.range || yAxis.range.length < 2) return;

        const x0 = new Date(xAxis.range[0]).getTime();
        const x1 = new Date(xAxis.range[1]).getTime();
        const y0 = Number(yAxis.range[0]);
        const y1 = Number(yAxis.range[1]);

        const xCenter = (x0 + x1) / 2;
        const yCenter = (y0 + y1) / 2;
        const xHalf = (x1 - x0) / 2;
        const yHalf = (y1 - y0) / 2;

        if (!Number.isFinite(xHalf) || !Number.isFinite(yHalf) || xHalf <= 0 || yHalf <= 0) return;

        Plotly.relayout(gd, {
            'xaxis.autorange': false,
            'yaxis.autorange': false,
            'xaxis.range[0]': new Date(xCenter - xHalf * 2),
            'xaxis.range[1]': new Date(xCenter + xHalf * 2),
            'yaxis.range[0]': yCenter - yHalf * 2,
            'yaxis.range[1]': yCenter + yHalf * 2,
        });
    }

    function pan(axisName, direction) {
        const axis = gd._fullLayout && gd._fullLayout[axisName] ? gd._fullLayout[axisName] : gd.layout[axisName];
        if (!axis || !axis.range || axis.range.length < 2) return;

        const isX = axisName === 'xaxis';
        const start = isX ? new Date(axis.range[0]).getTime() : Number(axis.range[0]);
        const end = isX ? new Date(axis.range[1]).getTime() : Number(axis.range[1]);
        const span = end - start;
        if (!Number.isFinite(span) || span === 0) return;

        const shift = span * 0.2 * direction;
        const update = {};
        update[axisName + '.autorange'] = false;
        if (isX) {
            update[axisName + '.range[0]'] = new Date(start + shift);
            update[axisName + '.range[1]'] = new Date(end + shift);
        } else {
            update[axisName + '.range[0]'] = start + shift;
            update[axisName + '.range[1]'] = end + shift;
        }
        Plotly.relayout(gd, update);
    }

    function addButton(text, axisName, direction) {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = text;
        button.style.padding = '4px 10px';
        button.style.border = '1px solid #c7c7c7';
        button.style.borderRadius = '4px';
        button.style.background = '#fff';
        button.style.cursor = 'pointer';
        button.addEventListener('click', () => pan(axisName, direction));
        controls.appendChild(button);
    }

    addButton('Left', 'xaxis', -1);
    addButton('Right', 'xaxis', 1);
    addButton('Up', 'yaxis', 1);
    addButton('Down', 'yaxis', -1);

    const zoomOutButton = document.createElement('button');
    zoomOutButton.type = 'button';
    zoomOutButton.textContent = 'Zoom Out x2';
    zoomOutButton.style.padding = '4px 10px';
    zoomOutButton.style.border = '1px solid #c7c7c7';
    zoomOutButton.style.borderRadius = '4px';
    zoomOutButton.style.background = '#fff';
    zoomOutButton.style.cursor = 'pointer';
    zoomOutButton.addEventListener('click', zoomOut);
    controls.appendChild(zoomOutButton);

    gd.parentNode.insertBefore(controls, gd);
})();
"""

    html = fig.to_html(
        full_html=True,
        include_plotlyjs="cdn",
        div_id="market-condition-chart",
        post_script=post_script,
    )
    html_path.write_text(html, encoding="utf-8")


def main() -> None:
    args = parse_args()
    csv_path = Path(args.csv)
    html_path = Path(args.out_html)
    conditions_path = Path(args.out_conditions)
    occurrences_path = Path(args.out_occurrences)

    if not csv_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {csv_path}")

    df = load_data(csv_path)
    hits = df[df["condition"]].copy()
    occurrences = build_occurrences(hits, args.gap_days)

    build_chart(df, occurrences, html_path, context_days=args.context_days)

    export_cols = ["timestamp", "close", "sma5", "sma20", "sma50", "sma200", "condition"]
    hits.to_csv(conditions_path, index=False, columns=export_cols)
    occurrences.to_csv(occurrences_path, index=False)

    print(f"Rows total: {len(df):,}")
    print(f"Condition matches: {len(hits):,}")
    print(f"Chart HTML: {html_path.resolve()}")
    print(f"Condition CSV: {conditions_path.resolve()}")
    print(f"Occurrence CSV: {occurrences_path.resolve()}")

    if not hits.empty:
        print("\nFirst 10 condition matches:")
        print(hits[export_cols].head(10).to_string(index=False))
        print("\nTop 10 occurrence windows (by length):")
        print(occurrences.sort_values(["days", "start"], ascending=[False, True]).head(10).to_string(index=False))


if __name__ == "__main__":
    main()
