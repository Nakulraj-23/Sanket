"""Q1 check 6: attack redact() with formats not in the probe file.

All formats are asserted. MISSED lists formats the first version missed; they are fixed now.
"""
import pytest

from sanket.pipeline.clean import clean

MASKED = [
    ("amex 3782 822463 10005", "CARD"), ("card no:4111111111111111.", "CARD"),
    ("card4111111111111111", "CARD"), ("my order was paid with card 4111111111111111", "CARD"),
    ("कार्ड ४१११ ११११ ११११ ११११", "CARD"), ("card ４１１１１１１１１１１１１１１１", "CARD"),
    ("call +91-98123-45678", "PHONE"), ("call +91 98123 45678", "PHONE"), ("call +91-9812345678", "PHONE"),
    ("call (+91) 9812345678", "PHONE"), ("call 0091 9812345678", "PHONE"), ("call 098123 45678", "PHONE"),
    ("uk +44 7911 123456", "PHONE"), ("phone9812345678now", "PHONE"),
    ("mail john.doe+bank@gmail.com", "EMAIL"), ("mail j.d.o.e@sub.mail.co.uk", "EMAIL"),
    ("mail JOHN_DOE@EXAMPLE.IN", "EMAIL"), ("mail mailto:x@y.io", "EMAIL"),
    ("account no 12345678", "ACCOUNT"), ("a/c 1234 5678 9012", "ACCOUNT"),
    ("sort code 12-34-56 account 87654321", "ACCOUNT"), ("iban GB82 WEST 1234 5698 7654 32", "ACCOUNT"),
    ("IBAN: DE89370400440532013000", "ACCOUNT"),
]
MISSED = [
    ("card 4111  1111  1111  1111 lost", "CARD"), ("card 4111 - 1111 - 1111 - 1111", "CARD"),
    ("card 4111.1111.1111.1111", "CARD"), ("card 4111/1111/1111/1111", "CARD"),
    ("ref 4111111111111111 is my card", "CARD"), ("call 98-12-34-56-78", "PHONE"),
    ("call 981 234 5678", "PHONE"), ("फोन ९८१२३४५६७८", "PHONE"), ("uk 07911 123456", "PHONE"),
    ("us (415) 555-2671", "PHONE"), ("mail john(at)gmail.com", "EMAIL"),
    ("iban gb82west12345698765432", "ACCOUNT"),
]
KEPT = ["on 2024-03-12 at 10:30 i paid 15,000", "pin 1234 and otp 567890", "transfer of 1000000000000 dong",
        "tracking 1Z999AA10123456784", "version 7.12.3 of app", "my balance is 7,500,000,000", "card ending 1111"]
FALSE_REDACTED = ["amount 6000000000", "i paid 9812345678 rupees"]


@pytest.mark.parametrize("text,kind", MASKED)
def test_masked(text, kind):
    assert kind in clean(text).pii


@pytest.mark.parametrize("text,kind", MISSED)
def test_formerly_missed(text, kind):
    assert kind in clean(text).pii


@pytest.mark.parametrize("text", KEPT)
def test_not_redacted(text):
    assert clean(text).pii == {}


@pytest.mark.parametrize("text", FALSE_REDACTED)
def test_amount_not_a_phone(text):
    assert clean(text).pii == {}
