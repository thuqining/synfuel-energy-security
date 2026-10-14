"""
coreset.py — ONE definition of the 30 core economies shown in every
main-text figure and table (the global aggregates use all assessed
economies; everything country-resolved uses this set).

The set is typed, so the paper can say in one sentence how it was
chosen, and every figure carries the same rows:

  large consumers            (8): the largest fuel users
  industrial importers       (6): exposed, land-poor importers of
                                  Europe and the Middle East (France was
                                  replaced by Israel in 2026-09: France
                                  and Spain were the closest pair in the
                                  whole set on every mechanism the paper
                                  distinguishes, and the Middle East had
                                  no net-importing member)
  emerging importers         (4): fast-growing import exposure
  island states              (5): no pipelines, no land transit
                                  (Fiji was replaced by Madagascar in
                                  2026-09: Fiji publishes no import-side
                                  fuel price with quantities; Madagascar
                                  is the same low-income, import-dependent
                                  island type and its hydrocarbon office
                                  publishes monthly landed CIF cost)
  resource-rich builders     (7): the exporters of the cost map, now
                                  including two archetypal oil-and-gas
                                  net exporters (Norway, Oman)

Within each type the members are the largest energy users of that
type with complete data; the list is fixed here so that no figure can
drift.  data/cost/core30.csv is written by write_core30() for the
record.
"""
from __future__ import annotations

import pandas as pd

from . import inputs

CORE30 = {
    "large consumer": ["China", "United States of America", "India",
                       "Japan", "Germany", "South Korea", "Brazil",
                       "Indonesia"],
    "industrial importer": ["Italy", "Spain", "Israel", "Netherlands",
                            "Poland", "United Kingdom"],
    "emerging importer": ["Vietnam", "Egypt", "Pakistan", "Kenya"],
    "island state": ["Philippines", "Sri Lanka",
                     "Dominican Republic", "Madagascar", "Ireland"],
    "resource-rich builder": ["Chile", "Morocco", "Australia",
                              "Saudi Arabia", "South Africa",
                              "Norway", "Oman"],
}
CORE30_LIST = [c for v in CORE30.values() for c in v]
CORE30_TYPE = {c: k for k, v in CORE30.items() for c in v}
assert len(CORE30_LIST) == 30 and len(set(CORE30_LIST)) == 30

# kept for the appendix / older scripts
ISLANDS = ["Japan", "United Kingdom", "Iceland", "Ireland",
           "New Zealand", "Singapore", "Philippines", "Indonesia",
           "Sri Lanka", "Taiwan", "Cuba", "Dominican Republic", "Haiti",
           "Jamaica", "Trinidad and Tobago", "Cyprus", "Malta",
           "Madagascar", "Papua New Guinea", "Fiji", "Mauritius",
           "Bahrain", "Solomon Islands", "Vanuatu"]


def core_countries(available, n: int = 30) -> list:
    """The core-30 economies present in `available`, in canonical order.
    `n` is accepted for backward compatibility and ignored: the set is
    fixed at 30 so every figure shows the same economies."""
    avail = set(available)
    picked = [c for c in CORE30_LIST if c in avail]
    missing = [c for c in CORE30_LIST if c not in avail]
    if missing:
        print(f"  core30: {len(missing)} not in this dataset -> "
              f"{missing}")
    return picked


def core_type(country: str) -> str:
    return CORE30_TYPE.get(country, "")


def is_case(countries) -> pd.Series:
    case = set(pd.read_csv(inputs.MAPS / "security_parity.csv").country)
    return pd.Series([c in case for c in countries], index=countries)


def write_core30() -> None:
    pd.DataFrame({"country": CORE30_LIST,
                  "type": [CORE30_TYPE[c] for c in CORE30_LIST]}) \
        .to_csv(inputs.MAPS / "core30.csv", index=False)
    print("wrote core30.csv")


if __name__ == "__main__":
    write_core30()
