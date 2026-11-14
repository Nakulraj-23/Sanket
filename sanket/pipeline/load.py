"""Read the raw Banking77 files into frames with the project's column names."""
import pandas as pd

from sanket.config import Settings


def _read(path) -> pd.DataFrame:
    """Read one raw CSV; the dataset's `category` column is called `intent` here."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    df = df.rename(columns={"category": "intent"})
    df.insert(0, "row_id", range(len(df)))
    return df[["row_id", "text", "intent"]]


def load_raw(raw_dir=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (official train, official test) with columns row_id, text, intent."""
    raw_dir = raw_dir or Settings().data_dir / "raw"
    return _read(raw_dir / "banking77_train.csv"), _read(raw_dir / "banking77_test.csv")
