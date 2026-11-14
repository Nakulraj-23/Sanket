"""Build data/splits/*.csv from the raw files (run with `make data`).

train 70% / val 15% / stream 15% come from the official train minus anything that also
appears in the official test; test is the official test, frozen.
"""
import pandas as pd
from sklearn.model_selection import train_test_split

from sanket.config import Settings
from sanket.pipeline.clean import clean
from sanket.pipeline.load import load_raw
from sanket.pipeline.quality import LEAK_COSINE, check_frame, check_splits
from sanket.pipeline.similarity import near_duplicates
from sanket.taxonomy import team_of


def _clean_frame(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Run the shared clean() on every text and give rows ids like tr-12."""
    out = df.copy()
    out["text"] = [clean(t).text for t in df["text"]]
    out["row_id"] = [f"{prefix}-{i}" for i in df["row_id"]]
    return out


def build_splits(seed: int = 42) -> tuple[dict[str, pd.DataFrame], dict[str, int]]:
    """Return the four splits and the counts of rows removed on the way."""
    raw_train, raw_test = load_raw()
    train = _clean_frame(raw_train, "tr")
    test = _clean_frame(raw_test, "te")
    overlap = train["text"].isin(set(test["text"]))
    removed = {"train_test_overlap": int(overlap.sum())}
    train = train[~overlap]
    removed["train_internal_duplicates"] = int(train["text"].duplicated().sum())
    train = train.drop_duplicates("text", keep="first")
    removed["test_internal_duplicates_kept"] = int(test["text"].duplicated().sum())
    leaked, _ = near_duplicates(test["text"].tolist(), train["text"].tolist(), LEAK_COSINE)
    removed["train_near_copies_of_test"] = len(leaked)
    train = train.drop(train.index[leaked])
    main, rest = train_test_split(train, test_size=0.30, stratify=train["intent"], random_state=seed)
    val, stream = train_test_split(rest, test_size=0.50, stratify=rest["intent"], random_state=seed)
    parts = {"train": main, "val": val, "stream": stream, "test": test}
    return {k: v.sort_values("row_id").reset_index(drop=True) for k, v in parts.items()}, removed


def main() -> None:
    """Build, check and write the splits, then print counts per split and per team."""
    splits, removed = build_splits(Settings().seed)
    for name, df in splits.items():
        check_frame(df, name, allow_duplicates=(name == "test"))
    check_splits(splits)
    out_dir = Settings().data_dir / "splits"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in splits.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)
    print("removed:", removed)
    teams = pd.DataFrame({n: df["intent"].map(team_of).value_counts() for n, df in splits.items()})
    print({n: len(df) for n, df in splits.items()})
    print(teams.fillna(0).astype(int).to_string())
    counts = splits["train"]["intent"].value_counts()
    print(f"train class count min {counts.min()} max {counts.max()}")


if __name__ == "__main__":
    main()
