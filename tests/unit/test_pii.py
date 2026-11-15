"""PII masking: Luhn, each kind, things that must stay, and the stress probe file."""
import pandas as pd

from sanket.config import Settings
from sanket.pipeline.pii import luhn_ok, redact


def test_luhn_known_numbers():
    assert luhn_ok("4111111111111111")
    assert luhn_ok("5555 5555 5555 4444")
    assert luhn_ok("378282246310005")
    assert not luhn_ok("4111111111111112")
    assert not luhn_ok("1234567890123456")
    assert not luhn_ok("7")


def test_card_needs_valid_checksum():
    assert redact("card 4111 1111 1111 1111")[0] == "card [CARD]"
    assert redact("card 4111 1111 1111 1112")[0] == "card 4111 1111 1111 1112"


def test_counts_by_kind():
    _, counts = redact("a@example.com b@example.com 9812345678")
    assert counts == {"EMAIL": 2, "PHONE": 1}


def test_amounts_dates_and_short_codes_stay():
    text = "paid rs 15000 on 12/03/2024, code AB12, pin 4321"
    assert redact(text) == (text, {})


def test_probe_file_all_rows_match():
    df = pd.read_csv(Settings().data_dir / "stress" / "pii_probe.csv", keep_default_na=False)
    assert len(df) == 71 and (df["kinds"] == "").sum() == 16
    for row in df.itertuples():
        masked, counts = redact(row.text)
        assert masked == row.expected_redacted, row.text
        assert sorted(counts) == sorted(k for k in row.kinds.split(";") if k), row.text
