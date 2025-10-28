\
import os
import pandas as pd
from datetime import datetime
from providers.base import DepositRecord
from scraper import run_aggregate

def to_dataframe(records: list[DepositRecord]) -> pd.DataFrame:
    df = pd.DataFrame([r.model_dump() for r in records])
    if df.empty:
        return df
    # нормализуем
    df["rate_apr"] = pd.to_numeric(df["rate_apr"], errors="coerce")
    df = df.dropna(subset=["rate_apr","currency","bank_name"])
    # сортировка по валюте и по убыванию ставки
    df = df.sort_values(by=["currency","rate_apr","bank_name"], ascending=[True, False, True])
    cols = ["currency","rate_apr","bank_name","product","country","link","source","fetched_at"]
    return df[cols]

def save_outputs(df: pd.DataFrame, out_dir="output"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(out_dir, f"deposit_rates_{ts}.csv")
    md_path = os.path.join(out_dir, f"deposit_rates_{ts}.md")
    df.to_csv(csv_path, index=False, encoding="utf-8")
    # Markdown table per currency
    with open(md_path, "w", encoding="utf-8") as f:
        for cur, chunk in df.groupby("currency"):
            f.write(f"## {cur}\n\n")
            f.write(chunk.to_markdown(index=False))
            f.write("\n\n")
    return csv_path, md_path

def main():
    records = run_aggregate()
    df = to_dataframe(records)
    if df.empty:
        print("No data collected. Check configs or sources.")
        return
    csv_path, md_path = save_outputs(df)
    print("Saved:")
    print(csv_path)
    print(md_path)

if __name__ == "__main__":
    main()
