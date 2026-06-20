"""Parse FIX protocol messages and output relevant fields to a CSV file."""

import argparse
import csv
import sys


def parse_fix_message(line: str) -> dict:
    """Parse a single FIX message line into a dictionary of tag-value pairs."""
    # Lines are formatted as: "timestamp : fix_message$"
    if " : " not in line:
        return {}

    _, message = line.split(" : ", 1)
    message = message.rstrip("$\n").strip()

    fields = {}
    # Support both the real SOH byte (0x01) and the two-char literal "^A"
    # that some text editors write when displaying/saving FIX files.
    raw = message.replace("^A", "\x01")
    for pair in raw.split("\x01"):
        if "=" in pair:
            tag, _, value = pair.partition("=")
            fields[tag.strip()] = value.strip()

    return fields


def load_fix_messages(input_fix_file: str) -> tuple[dict, list]:
    """Load and categorize FIX messages into orders and fills."""
    orders = {}   # ClOrdID -> fields
    fills = []    # list of fill field dicts

    with open(input_fix_file, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue

            fields = parse_fix_message(line)
            if not fields:
                continue

            msg_type = fields.get("35")

            # Capture NewOrderSingle (D) limit orders
            if msg_type == "D" and fields.get("40") == "2":
                clord_id = fields.get("11")
                if clord_id:
                    orders[clord_id] = fields

            # Capture full fills: ExecType=2, OrdStatus=2, OrdType=2
            elif (
                msg_type == "8"
                and fields.get("150") == "2"
                and fields.get("39") == "2"
                and fields.get("40") == "2"
            ):
                fills.append(fields)

    return orders, fills


def build_csv_rows(orders: dict, fills: list) -> list[dict]:
    """Match fills to their originating orders and build output rows.

    If no matching NewOrderSingle is found (execution-only logs), the fill
    itself carries all required fields (tag 44 = LimitPrice, tag 60 =
    TransactTime), so we fall back to those values.
    """
    rows = []

    for fill in fills:
        clord_id = fill.get("11")
        if not clord_id:
            continue

        # Use the matching order when available; otherwise fall back to the
        # fill itself (execution-only FIX logs don't include NewOrderSingle).
        order = orders.get(clord_id, fill)

        rows.append(
            {
                "OrderID": clord_id,
                "OrderTransactTime": order.get("60", ""),
                "ExecutionTransactTime": fill.get("60", ""),
                "Symbol": fill.get("55", ""),
                "Side": fill.get("54", ""),
                "OrderQty": fill.get("38", ""),
                "LimitPrice": order.get("44", ""),
                "AvgPx": fill.get("6", ""),
                "LastMkt": fill.get("30", ""),
            }
        )

    return rows


def write_csv(rows: list[dict], output_csv_file: str) -> None:
    """Write rows to a CSV file."""
    fieldnames = [
        "OrderID",
        "OrderTransactTime",
        "ExecutionTransactTime",
        "Symbol",
        "Side",
        "OrderQty",
        "LimitPrice",
        "AvgPx",
        "LastMkt",
    ]

    with open(output_csv_file, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """Entry point: parse arguments, process FIX file, write CSV."""
    parser = argparse.ArgumentParser(
        description="Parse FIX messages and output relevant fields to a CSV file."
    )
    parser.add_argument(
        "--input_fix_file",
        required=True,
        help="Path to the input FIX protocol file.",
    )
    parser.add_argument(
        "--output_csv_file",
        required=True,
        help="Path to the output CSV file.",
    )
    args = parser.parse_args()

    try:
        orders, fills = load_fix_messages(args.input_fix_file)
    except FileNotFoundError:
        print(f"Error: input file '{args.input_fix_file}' not found.", file=sys.stderr)
        sys.exit(1)

    rows = build_csv_rows(orders, fills)
    write_csv(rows, args.output_csv_file)

    print(f"Done. {len(rows)} fill(s) written to '{args.output_csv_file}'.")


if __name__ == "__main__":
    main()