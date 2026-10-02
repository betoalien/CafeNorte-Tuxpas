"""Small, temporary-file PRDX reproduction; does not modify PardoX or datos/."""

import argparse
import csv
import json
import tempfile
from pathlib import Path

import pardox as px


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--multiplier", type=int, default=5)
    parser.add_argument("--repeat", type=int, default=5)
    args = parser.parse_args()
    source = Path("datos/sales.csv")
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected = [f"{row['venta_id']}-{copy:02d}" for copy in range(args.multiplier) for row in rows]
    results = []
    with tempfile.TemporaryDirectory(prefix="pardox-prdx-repro-") as tmp:
        csv_path = Path(tmp) / "sales_scaled.csv"
        prdx_path = Path(tmp) / "sales.prdx"
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
            writer.writeheader()
            for copy in range(args.multiplier):
                for row in rows:
                    item = dict(row)
                    item["venta_id"] = f"{row['venta_id']}-{copy:02d}"
                    writer.writerow(item)
        for attempt in range(args.repeat):
            frame = px.read_csv(str(csv_path))
            frame.to_prdx(str(prdx_path))
            recovered = [row["venta_id"] for row in px.load_prdx(str(prdx_path)).to_dict()]
            mismatches = [
                {"position": i + 1, "expected": left, "loaded": right}
                for i, (left, right) in enumerate(zip(expected, recovered))
                if left != right
            ]
            mismatches.extend(
                {"position": i + 1, "expected": value, "loaded": None}
                for i, value in enumerate(expected[len(recovered) :], start=len(recovered))
            )
            results.append(
                {"attempt": attempt + 1, "rows": len(recovered), "mismatches": mismatches}
            )
    print(
        json.dumps(
            {"multiplier": args.multiplier, "source_rows": len(expected), "results": results},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
