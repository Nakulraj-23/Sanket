"""Intent taxonomy: the 77 intents, their teams and their urgency.

Team and urgency are this project's own rubric, not labels from the dataset.
"""
from pathlib import Path

import yaml

_PATH = Path(__file__).parent / "taxonomy.yaml"


def _load() -> dict:
    """Read taxonomy.yaml once at import time."""
    with open(_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


_RAW = _load()
TEAMS: dict[str, list[str]] = {t: list(v) for t, v in _RAW["teams"].items()}
TEAM_NAMES: list[str] = sorted(TEAMS)
INTENTS: list[str] = sorted(i for v in TEAMS.values() for i in v)
_TEAM_OF: dict[str, str] = {i: t for t, v in TEAMS.items() for i in v}
_URGENCY_OF: dict[str, str] = {i: "medium" for i in INTENTS}
for _level, _names in _RAW["urgency"].items():
    for _name in _names:
        _URGENCY_OF[_name] = _level


def team_of(intent: str) -> str:
    """Return the team that owns an intent (fails loudly on an unknown intent)."""
    return _TEAM_OF[intent]


def urgency_of(intent: str) -> str:
    """Return high, medium or low for an intent, from the project rubric."""
    return _URGENCY_OF[intent]


def taxonomy_payload() -> dict:
    """Shape returned by GET /taxonomy: teams to intents, and intent to urgency."""
    return {"teams": TEAMS, "urgency": dict(_URGENCY_OF)}
