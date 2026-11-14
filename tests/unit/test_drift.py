"""Drift maths: KS against scipy, PSI properties, report status rules."""
import numpy as np
import pytest
from scipy import stats

from sanket.monitoring.drift import drift_report, ks_2samp, psi


def _cases():
    r = np.random.default_rng(42)
    return [
        (r.normal(0, 1, 300), r.normal(0, 1, 500)),
        (r.normal(0, 1, 400), r.normal(0.3, 1, 400)),
        (r.integers(0, 10, 300).astype(float), r.integers(0, 12, 450).astype(float)),  # ties
        (r.exponential(1, 250), r.exponential(1.5, 600)),
        (np.round(r.normal(5, 2, 350)), np.round(r.normal(5.5, 2, 220))),  # ties, unequal
    ]


@pytest.mark.parametrize("i", range(5))
def test_ks_matches_scipy(i):
    a, b = _cases()[i]
    d, p = ks_2samp(a, b)
    ref = stats.ks_2samp(a, b)
    assert d == pytest.approx(ref.statistic, abs=1e-9)
    assert p == pytest.approx(ref.pvalue, abs=1e-3)


def test_psi_identical_is_zero_and_grows():
    r = np.random.default_rng(42)
    x = r.normal(0, 1, 2000)
    assert psi(x, x.copy()) == pytest.approx(0.0, abs=1e-12)
    small, big = psi(x, x + 0.3), psi(x, x + 1.0)
    assert 0 < small < big


def test_psi_hand_example():
    ref = np.array([1, 1, 1, 1, 2, 2, 2, 2, 3, 3])  # shares .4 .4 .2 in bins [0,1.5) [1.5,2.5) [2.5,4)
    live = np.array([1, 1, 2, 2, 2, 3, 3, 3, 3, 3])  # shares .2 .3 .5
    e, a = np.array([.4, .4, .2]), np.array([.2, .3, .5])
    expected = float(np.sum((a - e) * np.log(a / e)))
    assert psi(ref, live, bins=np.array([0, 1.5, 2.5, 4])) == pytest.approx(expected)


def _ref(r, n=1000):
    return {"n_tokens": r.poisson(11, n).tolist(), "oov_rate": r.beta(1, 30, n).tolist(),
            "team_conf": r.beta(8, 1, n).tolist(), "team_mix": {"A": 0.5, "B": 0.3, "C": 0.2}}


def test_report_statuses():
    r = np.random.default_rng(42)
    ref = _ref(r)
    assert drift_report(ref, _ref(r, 150))["status"] == "insufficient_data"
    assert drift_report(ref, _ref(r, 500))["status"] == "green"
    shifted = _ref(r, 500)
    shifted["oov_rate"] = r.beta(5, 20, 500).tolist()
    shifted["team_mix"] = {"A": 0.1, "B": 0.2, "C": 0.7}
    rep = drift_report(ref, shifted)
    assert rep["status"] == "red"
    assert {i["name"] for i in rep["indicators"]} == {"n_tokens", "oov_rate", "team_conf", "team_mix"}
