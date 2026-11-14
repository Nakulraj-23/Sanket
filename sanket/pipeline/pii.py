"""Mask personal data in a ticket before anything is stored or learned from.

Kinds masked: email, card number (only if the Luhn checksum passes), account
number (only when written next to a word like account or IBAN) and phone.
Raw text must never reach the database, a log or a model.
"""
import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
CARD_RE = re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")
ACCOUNT_RE = re.compile(
    r"(?i)\b(account|acct|a/c|ac)\b(?:\s*(?:no|number|num|nbr|#))?\.?\s*(?:is|:|-)?\s*(\d(?:[ -]?\d){7,17})(?!\d)"
)
IBAN_RE = re.compile(r"\b((?i:iban))\b\s*(?:(?i:is)|:)?\s*([A-Z]{2}\d{2}(?:\s?[A-Z0-9]{2,4}){3,8})")
ID_WORD_RE = re.compile(r"(?i)\b(order|ref|reference|tracking|invoice|txn|awb)\b[^\d]{0,12}$")
PHONE_INDIA_RE = re.compile(r"(?<![\d+])(?:(?:\+|00)?91[ -]?|0)?[6-9]\d{4}[ -]?\d{5}(?!\d)")
PHONE_INTL_RE = re.compile(r"(?<![\w+])\+\d[\d ()-]{7,16}\d(?!\d)")


def luhn_ok(number: str) -> bool:
    """Return True if the digits pass the Luhn checksum that real card numbers satisfy."""
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 2:
        return False
    total = 0
    for position, digit in enumerate(reversed(digits)):
        if position % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def _mask_card(match: re.Match) -> str:
    """Replace a digit run with [CARD] only when length and checksum fit a card.

    A number written right after "order", "ref", "tracking" and similar is an id, not a card.
    """
    digits = re.sub(r"\D", "", match.group(0))
    if ID_WORD_RE.search(match.string[: match.start()]):
        return match.group(0)  # a long order or reference id that happens to pass Luhn
    if 13 <= len(digits) <= 19 and luhn_ok(digits):
        return "[CARD]"
    return match.group(0)


def _mask_intl_phone(match: re.Match) -> str:
    """Replace a +country-code number with [PHONE] when it has 9 to 15 digits."""
    if 9 <= len(re.sub(r"\D", "", match.group(0))) <= 15:
        return "[PHONE]"
    return match.group(0)


def redact(text: str) -> tuple[str, dict[str, int]]:
    """Mask email, card, account and phone; return the masked text and counts by kind."""
    counts = {"EMAIL": 0, "PHONE": 0, "CARD": 0, "ACCOUNT": 0}

    def swap(kind: str):
        def inner(match: re.Match) -> str:
            counts[kind] += 1
            return f"[{kind}]"
        return inner

    def swap_after_word(match: re.Match) -> str:
        counts["ACCOUNT"] += 1
        return match.group(0).replace(match.group(2), "[ACCOUNT]")

    text = EMAIL_RE.sub(swap("EMAIL"), text)
    before = text
    text = CARD_RE.sub(_mask_card, text)
    counts["CARD"] = text.count("[CARD]") - before.count("[CARD]")
    text = ACCOUNT_RE.sub(swap_after_word, text)
    text = IBAN_RE.sub(swap_after_word, text)
    text = PHONE_INDIA_RE.sub(swap("PHONE"), text)
    before = text
    text = PHONE_INTL_RE.sub(_mask_intl_phone, text)
    counts["PHONE"] += text.count("[PHONE]") - before.count("[PHONE]")
    return text, {kind: n for kind, n in counts.items() if n}
