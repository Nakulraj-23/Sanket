"""Make noisy or Hinglish-looking copies of text, deterministically.

Output is synthetic. `hinglishify` feeds only the drift demo scenario; it is never
used for training or for any reported accuracy.
"""
import random
import re

# Longer phrases first so "not working" is replaced before "not".
PHRASES: dict[str, str] = {
    "not working": "kaam nahi kar raha",
    "has not arrived": "nahi aaya",
    "have not received": "nahi mila",
    "did not receive": "nahi mila",
    "how do i": "mujhe kaise",
    "how can i": "main kaise",
    "i want to": "mujhe karna hai",
    "i need to": "mujhe karna hai",
    "i would like to": "mujhe karna hai",
    "what is": "kya hai",
    "why is": "kyun hai",
    "where is": "kahan hai",
    "please help": "please madad karo",
    "thank you": "dhanyavaad",
    "bank account": "bank khata",
    "credit card": "credit card",
    "exchange rate": "exchange rate",
    "top up": "paisa daalna",
    "as soon as possible": "jaldi se jaldi",
    "i lost": "mera kho gaya",
    "someone stole": "kisi ne chura liya",
    "charged twice": "do baar kata",
    "money back": "paisa wapas",
    "is there": "kya hai",
    "i am": "main hu",
    "i have": "mere paas hai",
    "can you": "kya aap",
    "i cannot": "mujhse nahi ho raha",
    "i can't": "mujhse nahi ho raha",
    "still waiting": "abhi tak intezaar",
}
WORDS: dict[str, str] = {
    "my": "mera", "me": "mujhe", "i": "main", "money": "paisa", "card": "card", "account": "khata",
    "transfer": "transfer", "not": "nahi", "no": "nahi", "and": "aur", "or": "ya", "the": "",
    "is": "hai", "are": "hain", "was": "tha", "why": "kyun", "what": "kya", "when": "kab",
    "where": "kahan", "how": "kaise", "who": "kaun", "please": "please", "help": "madad",
    "problem": "dikkat", "issue": "dikkat", "wrong": "galat", "money,": "paisa,", "cash": "naqad",
    "stolen": "chori", "lost": "kho gaya", "phone": "phone", "pin": "pin", "password": "password",
    "yesterday": "kal", "today": "aaj", "tomorrow": "kal", "now": "abhi", "soon": "jaldi",
    "fast": "jaldi", "quickly": "jaldi", "urgent": "zaroori", "need": "chahiye", "want": "chahiye",
    "bank": "bank", "payment": "payment", "paid": "diya", "pay": "dena", "send": "bhejna",
    "sent": "bheja", "received": "mila", "receive": "milna", "refund": "refund", "fee": "charge",
    "charge": "charge", "charged": "kata", "deducted": "kata", "balance": "balance", "amount": "rakam",
    "limit": "limit", "cancel": "cancel", "delete": "hatana", "close": "band", "open": "kholna",
    "new": "naya", "old": "purana", "again": "phir", "twice": "do baar", "still": "abhi bhi",
    "waiting": "intezaar", "arrived": "aaya", "arrive": "aana", "show": "dikha", "showing": "dikh raha",
    "work": "kaam", "working": "kaam kar raha", "failed": "fail ho gaya", "declined": "reject hua",
    "pending": "pending", "can": "sakta", "cannot": "nahi sakta", "do": "karo", "does": "karta",
    "did": "kiya", "this": "yeh", "that": "woh", "with": "ke saath", "from": "se", "to": "ko",
    "for": "ke liye", "of": "ka", "in": "mein", "on": "par", "you": "aap", "your": "aapka",
    "we": "hum", "they": "woh", "have": "hai", "has": "hai", "get": "milna", "give": "dena",
    "tell": "batao", "know": "pata", "time": "samay", "day": "din", "days": "din", "week": "hafta",
    "month": "mahina", "daily": "roz", "statement": "statement", "address": "pata", "name": "naam",
    "identity": "pehchaan", "verify": "verify", "verification": "verification", "friend": "dost",
}
_PHRASE_RE = re.compile(
    r"\b(" + "|".join(re.escape(p) for p in sorted(PHRASES, key=len, reverse=True)) + r")\b", re.IGNORECASE
)
_ANY_RE = re.compile(_PHRASE_RE.pattern + r"|[A-Za-z']+", re.IGNORECASE)


def add_typos(text: str, rate: float, seed: int) -> str:
    """Swap, drop or duplicate characters inside words; `rate` is the chance per character."""
    rng = random.Random(seed)
    chars = list(text)
    out: list[str] = []
    i = 0
    while i < len(chars):
        c = chars[i]
        inside_word = c.isalpha() and i + 1 < len(chars) and chars[i + 1].isalpha()
        if inside_word and rng.random() < rate:
            action = rng.choice(["swap", "drop", "duplicate"])
            if action == "swap":
                out.extend([chars[i + 1], c])
                i += 2
                continue
            if action == "duplicate":
                out.extend([c, c])
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def hinglishify(text: str, seed: int) -> str:
    """Swap common English phrases and words for romanised Hindi (synthetic, for the drift demo).

    One pass, so Hindi words already written are not translated again. `seed` picks which
    eligible words are swapped (about 80%; phrases always), so output looks mixed, not uniform.
    """
    rng = random.Random(seed)

    def swap(match: re.Match) -> str:
        found = match.group(0)
        key = found.lower()
        if key in PHRASES:
            return PHRASES[key]
        if key in WORDS and rng.random() <= 0.8:
            return WORDS[key]
        return found

    return re.sub(r"\s+", " ", _ANY_RE.sub(swap, text)).strip()
