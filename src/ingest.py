"""Stage 1: fetch the raw dataset, verify its hash, and assert its shape.

Run: python -m src.ingest
"""
import hashlib
import sys
import urllib.request

import pandas as pd

from src.config import DATA_URL, RAW, RAW_SHA256

EXPECTED_MIN_ROWS = 700
REQUIRED_COLS = {"dteday", "cnt", "casual", "registered", "temp", "hum", "windspeed"}


def download(force: bool = False) -> None:
    if RAW.exists() and not force:
        return
    RAW.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(DATA_URL, RAW)


def raw_sha256() -> str:
    """SHA-256 of the raw file with line endings normalised to LF.

    Git with core.autocrlf=true checks the CSV out with CRLF on Windows,
    which changes the bytes but not the data. Normalising first means a
    fresh Windows clone matches RAW_SHA256 and any real edit still does not.
    """
    return hashlib.sha256(RAW.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def verify_raw() -> None:
    """Fail loudly if the raw file is not the one the results were built on.

    Shape checks in load_raw() miss a single edited value: one changed
    `temp` keeps every column and row and passes all the other tests.
    """
    actual = raw_sha256()
    if actual != RAW_SHA256:
        raise ValueError(
            f"{RAW.name} has changed: sha256 {actual[:16]}..., expected {RAW_SHA256[:16]}... "
            "Restore it with `git checkout -- data/raw/bike_daily.csv`."
        )


def load_raw() -> pd.DataFrame:
    df = pd.read_csv(RAW, parse_dates=["dteday"])
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"raw data is missing required columns: {sorted(missing)}")
    if len(df) < EXPECTED_MIN_ROWS:
        raise ValueError(f"raw data has only {len(df)} rows; expected >= {EXPECTED_MIN_ROWS}")
    return df


if __name__ == "__main__":
    download(force="--force" in sys.argv)
    verify_raw()
    df = load_raw()
    print(f"OK ingest: {len(df)} rows, {df.dteday.min().date()} -> {df.dteday.max().date()}, sha256 {RAW_SHA256[:16]}")
