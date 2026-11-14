"""Mask personal data in a ticket before anything is stored or learned from.

Kinds masked: email, card number (only if the Luhn checksum passes), account
number (only when written next to a word like account or IBAN) and phone.
Digits from any script are first turned into ASCII digits, and separators between
digit groups (spaces, dots, dashes, slashes) are tolerated, so formatting tricks do not hide a number.
Raw text must never reach the database, a log or a model.
"""
import re
import unicodedata

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
EMAIL_AT_RE = re.compile(r"(?i)[A-Za-z0-9._%+-]+\s?[(\[]at[)\]]\s?[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
CARD_RUN_RE = re.compile(r"(?<!\d)\d(?:[ .\-/]{0,3}\d){12,40}(?!\d)")
ACCOUNT_RE = re.compile(
    r"(?i)\b(account|acct|a/c|ac)\b(?:\s*(?:no|number|num|nbr|#))?\.?\s*(?:is|:|-)?\s*(\d(?:[ -]?\d){7,17})(?!\d)"
)
IBAN_RE = re.compile(
    r"(?i)\b(iban)\b\s*(?:is|:)?\s*([A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?)(?![A-Za-z0-9])"
)
ID_WORD_RE = re.compile(r"(?i)\b(order|tracking|invoice|txn|awb)\b[^\d]{0,12}$")
PHONE_INDIA_RE = re.compile(r"(?<![\d+])(?:(?:\+|00)?\(?\+?91\)?[ -]?|0)?[6-9]\d(?:[ -]?\d){8}(?!\d)")
PHONE_UK_RE = re.compile(r"(?<![\d+])07\d{3}[ -]?\d{6}(?!\d)")
PHONE_US_RE = re.compile(r"(?<![\d+])\(?[2-9]\d{2}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")
PHONE_INTL_RE = re.compile(r"(?<![\w+])\(?\+\d[\d ()-]{7,16}\d(?!\d)")
AMOUNT_BEFORE_RE = re.compile(r"(?i)\b(rs|inr|usd|eur|amount|paid|rupees)\.?\W{0,3}$|[$₹€£]\s?$")
AMOUNT_AFTER_RE = re.compile(r"(?i)^\s*(rupees|rs|inr|usd|eur|dollars|euros)\b")


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


def ascii_digits(text: str) -> str:
    """Turn digits of any script (Devanagari, Arabic-Indic, full-width) into 0-9."""
    return "".join(str(unicodedata.digit(c)) if c.isdecimal() and not c.isascii() else c for c in text)


def _find_card(run: str) -> tuple[int, int] | None:
    """Find the longest span of digit groups in `run` that is 13-19 digits and passes Luhn."""
    groups = [(m.start(), m.end()) for m in re.finditer(r"\d+", run)]
    for i in range(len(groups)):
        for j in range(len(groups) - 1, i - 1, -1):
            start, end = groups[i][0], groups[j][1]
            digits = re.sub(r"\D", "", run[start:end])
            if 13 <= len(digits) <= 19 and luhn_ok(digits):
                return start, end
    return None


def _mask_cards(text: str, counts: dict[str, int]) -> str:
    """Mask card numbers; an order, tracking or invoice number is an id, not a card."""
    def swap(match: re.Match) -> str:
        if ID_WORD_RE.search(match.string[: match.start()]):
            return match.group(0)
        run, out = match.group(0), ""
        while (span := _find_card(run)) is not None:
            counts["CARD"] += 1
            out += run[: span[0]] + "[CARD]"
            run = run[span[1]:]
        return out + run

    return CARD_RUN_RE.sub(swap, text)


def _mask_phones(text: str, counts: dict[str, int]) -> str:
    """Mask phone numbers; a long number used as an amount of money is left alone."""
    def swap(match: re.Match) -> str:
        before, after = match.string[: match.start()], match.string[match.end():]
        if AMOUNT_BEFORE_RE.search(before) or AMOUNT_AFTER_RE.search(after):
            return match.group(0)
        if match.re is PHONE_INTL_RE and not 9 <= len(re.sub(r"\D", "", match.group(0))) <= 15:
            return match.group(0)
        counts["PHONE"] += 1
        return "[PHONE]"

    for pattern in (PHONE_INTL_RE, PHONE_INDIA_RE, PHONE_UK_RE, PHONE_US_RE):
        text = pattern.sub(swap, text)
    return text


def redact(text: str) -> tuple[str, dict[str, int]]:
    """Mask email, card, account and phone; return the masked text and counts by kind."""
    counts = {"EMAIL": 0, "PHONE": 0, "CARD": 0, "ACCOUNT": 0}

    def swap_email(match: re.Match) -> str:
        counts["EMAIL"] += 1
        return "[EMAIL]"

    def swap_account(match: re.Match) -> str:
        counts["ACCOUNT"] += 1
        return match.group(0).replace(match.group(2), "[ACCOUNT]")

    text = ascii_digits(text)
    text = EMAIL_RE.sub(swap_email, text)
    text = EMAIL_AT_RE.sub(swap_email, text)
    text = _mask_cards(text, counts)
    text = ACCOUNT_RE.sub(swap_account, text)
    text = IBAN_RE.sub(swap_account, text)
    text = _mask_phones(text, counts)
    return text, {kind: n for kind, n in counts.items() if n}
