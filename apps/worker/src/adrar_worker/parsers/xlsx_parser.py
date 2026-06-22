"""
Deterministic XLSX/CSV parser.

Finds tabular data with recognisable column names and extracts activity facts.
No LLM involved. Confidence is based on how many required columns were matched.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date
from decimal import Decimal, InvalidOperation

import openpyxl

from .base import ExtractedFact

# Column name patterns (case-insensitive regex)
_COL_VALUE = re.compile(r"val(eur)?|consomm|quant(ity|ité)?|amount|qty|activit", re.I)
_COL_UNIT = re.compile(r"unit|unité|unite", re.I)
_COL_CATEGORY = re.compile(r"categ|catég|type|poste|source|fuel|energy|énergie", re.I)
_COL_PERIOD_START = re.compile(r"start|début|from|date_start|period_start|début_période", re.I)
_COL_PERIOD_END = re.compile(r"end|fin|to|date_end|period_end|fin_période", re.I)
_COL_DATE = re.compile(r"^date$|^période$|^period$|^year$|^année$|^mois$", re.I)
_COL_SCOPE = re.compile(r"scope|portée", re.I)
_COL_SCOPE2 = re.compile(r"scope2_type|s2_type|market|location", re.I)
_COL_FUEL = re.compile(r"fuel|carburant|combustible", re.I)

_SCOPE_MAP = {"scope1": 1, "scope2": 2, "scope3": 3, "1": 1, "2": 2, "3": 3}


def _match_col(headers: list[str], pattern: re.Pattern) -> int | None:
    """Return the index of the first header matching pattern, or None."""
    for i, h in enumerate(headers):
        if pattern.search(str(h).strip()):
            return i
    return None


def _parse_decimal(val: str) -> Decimal | None:
    if not val or str(val).strip() in ("", "-", "N/A", "n/a"):
        return None
    try:
        return Decimal(str(val).replace(",", ".").replace(" ", "").strip())
    except InvalidOperation:
        return None


def _parse_date(val: str) -> date | None:
    if not val:
        return None
    val = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    # Year only → full year
    try:
        year = int(val)
        if 2000 <= year <= 2099:
            return date(year, 1, 1)
    except ValueError:
        pass
    return None


def _rows_to_facts(
    headers: list[str],
    rows: list[list],
    doc_id: str,
    filename: str,
    page: int = 0,
) -> list[ExtractedFact]:
    """Map a table (headers + rows) to ExtractedFact objects."""
    i_val = _match_col(headers, _COL_VALUE)
    i_unit = _match_col(headers, _COL_UNIT)
    i_cat = _match_col(headers, _COL_CATEGORY)
    i_start = _match_col(headers, _COL_PERIOD_START)
    i_end = _match_col(headers, _COL_PERIOD_END)
    i_date = _match_col(headers, _COL_DATE)
    i_scope = _match_col(headers, _COL_SCOPE)
    i_scope2 = _match_col(headers, _COL_SCOPE2)
    i_fuel = _match_col(headers, _COL_FUEL)

    # Required: value + unit; category gets a default if missing
    if i_val is None or i_unit is None:
        return []

    # Confidence based on how many optional columns were found
    found = sum(x is not None for x in [i_cat, i_start or i_date, i_scope, i_fuel])
    confidence = min(0.5 + found * 0.1, 0.95)

    facts: list[ExtractedFact] = []
    for row in rows:
        # Use default arg to bind row to the closure (avoids B023 late-binding issue)
        def cell(idx: int | None, _row: list = row) -> str:  # noqa: B008
            if idx is None or idx >= len(_row):
                return ""
            return str(_row[idx]).strip() if _row[idx] is not None else ""

        value = _parse_decimal(cell(i_val))
        if value is None or value == 0:
            continue

        unit = cell(i_unit) or "unknown"
        category = cell(i_cat) or "scope1_stationary"

        # Period
        if i_start is not None:
            period_start = _parse_date(cell(i_start)) or date(2024, 1, 1)
        elif i_date is not None:
            period_start = _parse_date(cell(i_date)) or date(2024, 1, 1)
        else:
            period_start = date(2024, 1, 1)

        if i_end is not None:
            period_end = _parse_date(cell(i_end)) or date(2024, 12, 31)
        else:
            period_end = date(period_start.year, 12, 31)

        # Scope
        scope_raw = cell(i_scope).lower().replace(" ", "")
        scope = _SCOPE_MAP.get(scope_raw, 1)

        scope2_type: str | None = None
        if scope == 2:
            s2_raw = cell(i_scope2).lower()
            if "market" in s2_raw or "marché" in s2_raw:
                scope2_type = "market"
            elif "location" in s2_raw or "réseau" in s2_raw:
                scope2_type = "location"

        fuel_type = cell(i_fuel) or None

        facts.append(
            ExtractedFact(
                category=category,
                activity_value=value,
                activity_unit=unit,
                period_start=period_start,
                period_end=period_end,
                scope=scope,
                scope2_type=scope2_type,
                fuel_type=fuel_type,
                confidence=confidence,
                source_page=page,
                raw_text=str(row),
            )
        )
    return facts


def parse_xlsx(content: bytes, doc_id: str, filename: str) -> list[ExtractedFact]:
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    facts: list[ExtractedFact] = []
    for sheet_num, sheet in enumerate(wb.worksheets):
        rows_data = list(sheet.iter_rows(values_only=True))
        if not rows_data:
            continue
        headers = [str(c).strip() if c is not None else "" for c in rows_data[0]]
        data_rows = [list(r) for r in rows_data[1:] if any(c is not None for c in r)]
        facts.extend(_rows_to_facts(headers, data_rows, doc_id, filename, page=sheet_num))
    return facts


def parse_csv(content: bytes, doc_id: str, filename: str) -> list[ExtractedFact]:
    text = content.decode("utf-8", errors="replace")
    # Detect delimiter
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|") if sample.strip() else None
    except csv.Error:
        dialect = None
    reader = csv.reader(io.StringIO(text), dialect or csv.get_dialect("excel"))
    rows = list(reader)
    if not rows:
        return []
    headers = [h.strip() for h in rows[0]]
    data_rows = [r for r in rows[1:] if any(c.strip() for c in r)]
    return _rows_to_facts(headers, data_rows, doc_id, filename, page=0)
