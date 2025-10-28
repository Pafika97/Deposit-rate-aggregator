\
import re
import time
import json
import yaml
import math
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Any
from datetime import datetime, timezone

from providers.base import DepositRecord

def _json_get_path(obj: Any, path: str):
    # very tiny JSONPath-ish: "$" (root), "$.a", "$.a.b", "$.items[0]"
    if path in (None, "", "$"):
        return obj
    cur = obj
    for part in path.strip("$.").split("."):
        if "[" in part and part.endswith("]"):
            key, idx = part[:-1].split("[")
            if key:
                cur = cur.get(key, {})
            cur = cur[int(idx)]
        else:
            cur = cur.get(part, {})
    return cur

def _to_float_rate(val):
    if val is None:
        return None
    if isinstance(val, (int,float)):
        return float(val)
    s = str(val).strip()
    m = re.search(r'([0-9]+[.,]?[0-9]*)', s)
    if not m:
        return None
    num = m.group(1).replace(",", ".")
    return float(num)

def fetch_json(src: Dict[str, Any]) -> List[DepositRecord]:
    url = src["url"]
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    lst = _json_get_path(data, src["json_map"].get("list_path","$"))
    out = []
    for item in lst:
        fields = src["json_map"]["fields"]
        rec = DepositRecord(
            bank_name = _json_get_path(item, fields["bank_name"]),
            country = src.get("country"),
            currency = _json_get_path(item, fields.get("currency")) or (src.get("currency_hint") or [""])[0],
            product = _json_get_path(item, fields.get("product")),
            rate_apr = float(_to_float_rate(_json_get_path(item, fields["rate_apr"]))),
            link = _json_get_path(item, fields.get("link")),
            source = src.get("name"),
            fetched_at = datetime.now(timezone.utc).isoformat()
        )
        out.append(rec)
    return out

def fetch_static_html(src: Dict[str, Any]) -> List[DepositRecord]:
    url = src["url"]
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    rows_sel = src["html"]["rows"]["selector"]
    rows = soup.select(rows_sel)
    out = []
    for row in rows:
        def field_value(field_def):
            if "value" in field_def and field_def["value"] is not None:
                return field_def["value"]
            el = row.select_one(field_def.get("selector")) if field_def.get("selector") else None
            if not el:
                return None
            if field_def.get("attr"):
                val = el.get(field_def["attr"])
            else:
                val = el.get_text(" ", strip=True)
            rx = field_def.get("regex")
            if rx:
                m = re.search(rx, val or "")
                if m:
                    return m.group(1)
            return val
        fields = src["html"]["fields"]
        currency = field_value(fields.get("currency", {"value": (src.get("currency_hint") or [""])[0]}))
        rate = _to_float_rate(field_value(fields["rate_apr"]))
        if rate is None:
            continue
        rec = DepositRecord(
            bank_name = field_value(fields.get("bank_name", {"value": src.get("name")})),
            country = src.get("country"),
            currency = currency or (src.get("currency_hint") or [""])[0],
            product = field_value(fields.get("product", {"value": None})),
            rate_apr = float(rate),
            link = urljoin(url, field_value(fields.get("link", {"value": url})) or url),
            source = src.get("name"),
            fetched_at = datetime.now(timezone.utc).isoformat()
        )
        out.append(rec)
    return out

def fetch_playwright(src: Dict[str, Any]) -> List[DepositRecord]:
    # Lazy import to avoid dependency if not used
    from playwright.sync_api import sync_playwright
    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(src["url"], timeout=60000)
        wait_for = src["playwright"].get("wait_for")
        if wait_for:
            page.wait_for_selector(wait_for, timeout=60000)
        rows_selector = src["playwright"]["rows_selector"]
        rows = page.query_selector_all(rows_selector)
        fields = src["playwright"]["fields"]
        for row in rows:
            def get_val(defn):
                if "value" in defn and defn["value"] is not None:
                    return defn["value"]
                elem = row.query_selector(defn.get("selector")) if defn.get("selector") else None
                if not elem:
                    return None
                val = elem.get_attribute(defn["attr"]) if defn.get("attr") else (elem.inner_text() or "").strip()
                rx = defn.get("regex")
                if rx:
                    m = re.search(rx, val or "")
                    if m:
                        return m.group(1)
                return val
            currency = get_val(fields.get("currency", {"value": (src.get("currency_hint") or [""])[0]}))
            rate = _to_float_rate(get_val(fields["rate_apr"]))
            if rate is None:
                continue
            link_val = get_val(fields.get("link", {"value": src["url"]})) or src["url"]
            rec = DepositRecord(
                bank_name = get_val(fields.get("bank_name", {"value": src.get("name")})),
                country = src.get("country"),
                currency = currency or (src.get("currency_hint") or [""])[0],
                product = get_val(fields.get("product", {"value": None})),
                rate_apr = float(rate),
                link = link_val if link_val.startswith("http") else urljoin(src["url"], link_val),
                source = src.get("name"),
                fetched_at = datetime.now(timezone.utc).isoformat()
            )
            out.append(rec)
        browser.close()
    return out

def fetch_csv_local(src: Dict[str, Any]) -> List[DepositRecord]:
    import pandas as pd
    df = pd.read_csv(src["path"])
    out = []
    for _, r in df.iterrows():
        out.append(DepositRecord(
            bank_name = str(r.get("bank_name")),
            country = r.get("country"),
            currency = str(r.get("currency")),
            product = r.get("product"),
            rate_apr = float(r.get("rate_apr")),
            link = r.get("link"),
            source = r.get("source","manual"),
            fetched_at = datetime.now(timezone.utc).isoformat()
        ))
    return out

FETCHERS = {
    "json": fetch_json,
    "static_html": fetch_static_html,
    "playwright": fetch_playwright,
    "csv": fetch_csv_local,
}

def run_aggregate(config_path="banks.yaml") -> list[DepositRecord]:
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    records: List[DepositRecord] = []
    for src in cfg.get("sources", []):
        t = src.get("type")
        if t not in FETCHERS:
            print(f"⚠️  Unsupported source type: {t} ({src.get('name')})")
            continue
        try:
            recs = FETCHERS[t](src)
            records.extend(recs)
            print(f"✓ {src.get('name')} -> {len(recs)} records")
        except Exception as e:
            print(f"✗ {src.get('name')} failed: {e}")
    return records

if __name__ == "__main__":
    out = run_aggregate()
    print(f"Total collected: {len(out)}")
