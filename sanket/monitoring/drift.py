"""Drift maths in plain NumPy: PSI, a two-sample KS test, and the report built from them.

Drift means the tickets arriving now no longer look like the validation tickets the model
was tuned on. We compare a few simple signals and call the result green, amber or red.
"""
from datetime import UTC, datetime

import numpy as np

MIN_TICKETS = 200
EMPTY_BIN = 1e-4
_RANK = {"green": 0, "amber": 1, "red": 2}


def bin_edges(reference: np.ndarray, n_bins: int = 10) -> np.ndarray:
    """Cut points that put roughly equal numbers of reference values in each bin."""
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, n_bins + 1)))
    if len(edges) < 2:  # all values equal: one bin around that value
        edges = np.array([edges[0] - 0.5, edges[0] + 0.5])
    edges[0], edges[-1] = -np.inf, np.inf  # live values outside the range still count
    return edges


def _shares(values: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Share of values in each bin; an empty bin gets a small floor so the log is defined."""
    counts, _ = np.histogram(values, bins=edges)
    return np.maximum(counts / max(len(values), 1), EMPTY_BIN)


def psi_from_shares(expected: np.ndarray, actual: np.ndarray) -> float:
    """PSI = sum over bins of (actual - expected) * ln(actual / expected)."""
    e = np.maximum(np.asarray(expected, dtype=float), EMPTY_BIN)
    a = np.maximum(np.asarray(actual, dtype=float), EMPTY_BIN)
    return float(np.sum((a - e) * np.log(a / e)))


def psi(expected: np.ndarray, actual: np.ndarray, bins=10) -> float:
    """Population Stability Index of two samples.

    `bins` is a number of reference-quantile bins or an array of edges. Both samples use
    the same edges, taken from the reference, so the bins mean the same thing for both.
    """
    expected, actual = np.asarray(expected, float), np.asarray(actual, float)
    edges = bin_edges(expected, bins) if np.isscalar(bins) else np.asarray(bins, float)
    return psi_from_shares(_shares(expected, edges), _shares(actual, edges))


def _kolmogorov_sf(lam: float) -> float:
    """P(K > lam) for the Kolmogorov distribution: 2 * sum (-1)^(k-1) exp(-2 k^2 lam^2)."""
    if lam < 0.2:
        return 1.0
    k = np.arange(1, 101)
    total = 2.0 * np.sum((-1.0) ** (k - 1) * np.exp(-2.0 * k**2 * lam**2))
    return float(min(max(total, 0.0), 1.0))


def _exact_sf(d: float, n: int, m: int) -> float:
    """Exact P(D >= d) for sample sizes n and m, by walking the two sorted samples as a lattice path.

    A path steps right for a point of sample a and up for a point of sample b. The CDF gap
    at step (i, j) is i/n - j/m. We count (as probabilities) the paths that never reach gap d,
    one anti-diagonal at a time, and return the share that did reach it.
    """
    h = round(d * n * m)  # a gap of d means |i*m - j*n| >= h
    prob = np.ones(1)  # probability of being at (i, s - i) on diagonal s, staying inside the band
    for s in range(1, n + m + 1):
        i = np.arange(max(0, s - m), min(n, s) + 1)
        new = np.zeros(len(i))
        prev_lo = max(0, s - 1 - m)
        left = i - 1 - prev_lo  # came from (i-1, j): a step right
        ok = (left >= 0) & (left < len(prob))
        new[ok] += prob[left[ok]] * i[ok] / s
        down = i - prev_lo  # came from (i, j-1): a step up
        ok = (down >= 0) & (down < len(prob)) & (i <= s - 1) & (s - i >= 1)
        new[ok] += prob[down[ok]] * (s - i[ok]) / s
        new[np.abs(i * m - (s - i) * n) >= h] = 0.0  # outside the band
        prob = new
    return float(min(max(1.0 - prob[-1], 0.0), 1.0))


def ks_2samp(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    """Two-sample Kolmogorov-Smirnov test: largest gap between the two empirical CDFs.

    Walk the merged sorted values; at each value the CDF of a sample is the share of its
    points at or below that value. D is the biggest difference. The p-value is exact for
    up to a million sample pairs (like scipy); beyond that the asymptotic Kolmogorov series.
    """
    a, b = np.sort(np.asarray(a, float)), np.sort(np.asarray(b, float))
    merged = np.concatenate([a, b])
    cdf_a = np.searchsorted(a, merged, side="right") / len(a)
    cdf_b = np.searchsorted(b, merged, side="right") / len(b)
    d = float(np.max(np.abs(cdf_a - cdf_b)))
    en = np.sqrt(len(a) * len(b) / (len(a) + len(b)))
    if len(a) * len(b) <= 1_000_000:
        return d, _exact_sf(d, len(a), len(b))
    return d, _kolmogorov_sf((en + 0.12 + 0.11 / en) * d)


def ks_status(d: float, p: float) -> str:
    """red if D >= 0.2 and p < 0.01; amber if D >= 0.1 and p < 0.01; else green."""
    if p < 0.01 and d >= 0.2:
        return "red"
    if p < 0.01 and d >= 0.1:
        return "amber"
    return "green"


def psi_status(value: float) -> str:
    """green under 0.1, amber up to 0.25, red above."""
    if value < 0.1:
        return "green"
    return "amber" if value <= 0.25 else "red"


def _ks_indicator(name: str, ref: list, live: list) -> dict:
    """Run KS on one signal and label the result."""
    d, p = ks_2samp(np.array(ref), np.array(live))
    return {"name": name, "kind": "ks", "value": round(d, 4), "p_value": round(p, 6),
            "status": ks_status(d, p)}


def _mix_indicator(ref_mix: dict, live_mix: dict) -> tuple[dict, dict]:
    """PSI over predicted-team shares; also returns the per-team table for the report."""
    teams = sorted(set(ref_mix) | set(live_mix))
    e = np.array([ref_mix.get(t, 0.0) for t in teams])
    a = np.array([live_mix.get(t, 0.0) for t in teams])
    value = psi_from_shares(e, a)
    ind = {"name": "team_mix", "kind": "psi", "value": round(value, 4), "p_value": None,
           "status": psi_status(value)}
    table = {t: {"reference": round(float(x), 4), "live": round(float(y), 4)}
             for t, x, y in zip(teams, e, a)}
    return ind, table


def drift_report(reference: dict, live: dict, model_version: str = "v1") -> dict:
    """Compare live tickets with the reference and return the DriftReport dict.

    Both dicts hold n_tokens, oov_rate, team_conf (lists of raw values) and team_mix
    (share per predicted team). Overall status is the worst indicator; under 200 live
    tickets we only say there is not enough data.
    """
    n = len(live["n_tokens"])
    base = {"created_at": datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds"),
            "n_tickets": n, "model_version": model_version}
    if n < MIN_TICKETS:
        return {**base, "status": "insufficient_data", "indicators": [], "team_mix": {},
                "message": f"Only {n} tickets so far; at least {MIN_TICKETS} are needed."}
    inds = [_ks_indicator(k, reference[k], live[k]) for k in ("n_tokens", "oov_rate", "team_conf")]
    mix, table = _mix_indicator(reference["team_mix"], live["team_mix"])
    inds.append(mix)
    worst = max(inds, key=lambda i: _RANK[i["status"]])
    status = worst["status"]
    msg = ("No meaningful change against the reference." if status == "green"
           else f"{worst['name']} has moved away from the reference ({status}).")
    return {**base, "status": status, "indicators": inds, "team_mix": table, "message": msg}
