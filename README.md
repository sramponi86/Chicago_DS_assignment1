# FIX Protocol Parser and Execution Metrics

Two command-line tools for processing FIX 4.2 execution logs. The first parses a raw FIX file and extracts filled orders into a CSV. The second reads that CSV and produces per-exchange performance statistics.

---

## Requirements

- Python 3.10 or later
- pandas

Install dependencies with:

```
pip install pandas
```

---

## fix_to_csv.py

Reads a FIX 4.2 log file and writes one row per filled limit order to a CSV file.

### What it does

The parser goes through each line of the FIX file and picks out two message types:

- `NewOrderSingle` (MsgType 35=D) with OrdType Limit (40=2) — these are the original orders
- `ExecutionReport` (MsgType 35=8) where ExecType is Fill (150=2) and OrdStatus is Filled (39=2) — these are the completed executions

Partial fills (39=1) are ignored. For each full fill, the program looks up the matching original order by ClOrdID and combines fields from both into a single output row. If the log does not contain NewOrderSingle messages (execution-only logs), the fill message itself is used as a fallback.

The field delimiter is the SOH character (0x01). Both the raw binary SOH and the text representation `^A` are handled automatically.

### Usage

```
python fix_to_csv.py --input_fix_file <path_to_fix_file> --output_csv_file <path_to_output_csv>
```

Example:

```
python fix_to_csv.py --input_fix_file /opt/assignment1/trading.fix --output_csv_file fills.csv
```

### Output format

```
OrderID,OrderTransactTime,ExecutionTransactTime,Symbol,Side,OrderQty,LimitPrice,AvgPx,LastMkt
ID1542,20250910-08:00:00.377,20250910-08:00:00.509,YANG,1,27,23.700000,23.170000,ID1516
```

Column reference:

| Column | FIX Tag | Description |
|---|---|---|
| OrderID | 11 | Client order identifier |
| OrderTransactTime | 60 | Timestamp from the original order |
| ExecutionTransactTime | 60 | Timestamp from the execution report |
| Symbol | 55 | Ticker symbol |
| Side | 54 | 1 = Buy, 2 = Sell |
| OrderQty | 38 | Quantity ordered |
| LimitPrice | 44 | The limit price set on the order |
| AvgPx | 6 | Average execution price |
| LastMkt | 30 | Exchange or broker identifier |

---

## calc_execution_metrics.py

Reads the fills CSV produced by `fix_to_csv.py` and outputs a summary of execution quality per exchange.

### What it does

For each exchange (identified by the LastMkt column), the program calculates:

- **Average price improvement**: the difference between the limit price and the average execution price, adjusted for side. Buy orders improve when filled below the limit; sell orders improve when filled above it. The result is always zero or positive.
- **Average execution speed**: the average time in seconds between order submission and fill, computed from the two timestamp columns.

### Usage

```
python calc_execution_metrics.py --input_csv_file <path_to_fills_csv> --output_metrics_file <path_to_output_csv>
```

Example:

```
python calc_execution_metrics.py --input_csv_file fills.csv --output_metrics_file metrics.csv
```

### Output format

```
LastMkt,AvgPriceImprovement,AvgExecSpeedSecs
ID1516,0.0255,519.63
ID245333,0.1319,28.47
```

---

## Typical workflow

```
python fix_to_csv.py --input_fix_file trading.fix --output_csv_file fills.csv
python calc_execution_metrics.py --input_csv_file fills.csv --output_metrics_file metrics.csv
```
