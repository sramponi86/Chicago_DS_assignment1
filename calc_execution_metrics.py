"""Calculate per-exchange execution speed and price improvement from a fills CSV."""

import argparse
import sys

import pandas as pd


TIMESTAMP_FORMAT = "%Y%m%d-%H:%M:%S.%f"

# FIX Side values
SIDE_BUY = 1
SIDE_SELL = 2


def load_executions(input_csv_file: str) -> pd.DataFrame:
    """Load the executions CSV and parse timestamp columns."""
    try:
        df = pd.read_csv(input_csv_file)
    except FileNotFoundError:
        print(f"Error: input file '{input_csv_file}' not found.", file=sys.stderr)
        sys.exit(1)

    for col in ("OrderTransactTime", "ExecutionTransactTime"):
        df[col] = pd.to_datetime(df[col], format=TIMESTAMP_FORMAT)

    for col in ("LimitPrice", "AvgPx"):
        df[col] = pd.to_numeric(df[col])

    df["Side"] = pd.to_numeric(df["Side"])

    return df


def compute_price_improvement(df: pd.DataFrame) -> pd.Series:
    """
    Return per-row price improvement.

    Buy orders: improvement = LimitPrice - AvgPx  (paid less than the limit)
    Sell orders: improvement = AvgPx - LimitPrice (received more than the limit)
    """
    buy_mask = df["Side"] == SIDE_BUY
    improvement = pd.Series(0.0, index=df.index)
    improvement[buy_mask] = df.loc[buy_mask, "LimitPrice"] - df.loc[buy_mask, "AvgPx"]
    improvement[~buy_mask] = df.loc[~buy_mask, "AvgPx"] - df.loc[~buy_mask, "LimitPrice"]
    return improvement


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate average price improvement and execution speed per exchange."""
    df = df.copy()
    df["PriceImprovement"] = compute_price_improvement(df)
    df["ExecSpeedSecs"] = (
        df["ExecutionTransactTime"] - df["OrderTransactTime"]
    ).dt.total_seconds()

    metrics = (
        df.groupby("LastMkt")
        .agg(
            AvgPriceImprovement=("PriceImprovement", "mean"),
            AvgExecSpeedSecs=("ExecSpeedSecs", "mean"),
        )
        .reset_index()
    )

    return metrics


def write_metrics(metrics: pd.DataFrame, output_metrics_file: str) -> None:
    """Write the metrics DataFrame to a CSV file."""
    metrics.to_csv(output_metrics_file, index=False)


def main() -> None:
    """Entry point: parse arguments, compute metrics, write output."""
    parser = argparse.ArgumentParser(
        description="Calculate per-exchange execution speed and price improvement."
    )
    parser.add_argument(
        "--input_csv_file",
        required=True,
        help="Path to the input fills CSV file.",
    )
    parser.add_argument(
        "--output_metrics_file",
        required=True,
        help="Path to the output metrics CSV file.",
    )
    args = parser.parse_args()

    df = load_executions(args.input_csv_file)
    metrics = compute_metrics(df)
    write_metrics(metrics, args.output_metrics_file)

    print(
        f"Done. Metrics for {len(metrics)} exchange(s) written to "
        f"'{args.output_metrics_file}'."
    )


if __name__ == "__main__":
    main()
