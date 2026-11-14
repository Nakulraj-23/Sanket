"""clean() and validate(): normal form, idempotence, Devanagari, validation problems."""
import pytest

from sanket.pipeline.clean import clean, validate


def test_normalises_case_space_and_unicode():
    result = clean("  My   CARD\tis   not working  ")
    assert result.text == "my card is not working"
    assert result.n_tokens == 5 and result.n_chars == len(result.text)
    assert clean("ＭＹ ｃａｒｄ").text == "my card"


def test_placeholders_survive_lowercasing():
    result = clean("Mail Me@Example.com or CALL 9812345678")
    assert result.text == "mail [EMAIL] or call [PHONE]"
    assert result.pii == {"EMAIL": 1, "PHONE": 1}


def test_keeps_devanagari():
    assert clean("मेरा  कार्ड चोरी हो गया").text == "मेरा कार्ड चोरी हो गया"


@pytest.mark.parametrize("raw", [
    "My CARD 4111 1111 1111 1111 is Lost!", "mail x@example.com  now", "मेरा  Card", "Rs 5,000 on 12/03",
    "account number 123456789012 and 9812345678", "[email] literal",
])
def test_clean_is_idempotent(raw):
    once = clean(raw).text
    assert clean(once).text == once


def test_validate():
    assert validate("my card is lost") == []
    assert validate("मेरा कार्ड") == []
    assert validate("")[0].startswith("empty")
    assert validate("   ")[0].startswith("empty")
    assert validate("12345 !!!")[0].startswith("no_letters")
    assert validate("a" * 2001)[0].startswith("too_long")
