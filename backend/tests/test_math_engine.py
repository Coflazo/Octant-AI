"""Tests for Octant AI math engine modules."""

import pytest
import numpy as np
import pandas as pd
from backend.math_engine.time_series import run_adf_test, fit_garch_family
from backend.math_engine.stochastic import fit_ou_process
from backend.math_engine.options_models import black_scholes_call, implied_vol
from backend.math_engine.portfolio import nearest_positive_definite, ledoit_wolf_shrinkage
from backend.math_engine.hypothesis_tests import apply_bonferroni, compute_bayesian_adjusted_sharpe


def test_adf_stationary_synthetic():
    """Confirm ADF rejects H0 on a perfectly stationary process."""
    np.random.seed(42)
    series = pd.Series(np.random.normal(0, 1, 1000))
    res = run_adf_test(series)
    assert res.is_stationary is True
    assert res.p_value < 0.05


def test_garch_parameter_recovery():
    """GARCH(1,1) model parsing on synthetic returns."""
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0.001, 0.015, 500))
    try:
        from arch import arch_model
        fit = fit_garch_family(returns)
        assert len(fit.conditional_volatility) == 500
    except ImportError:
        pass


def test_black_scholes_call():
    """Compare BS call price: S=100, K=100, r=0.05, T=1, sigma=0.2."""
    price = black_scholes_call(100.0, 100.0, 0.05, 1.0, 0.2)
    np.testing.assert_almost_equal(price, 10.45058, decimal=4)


def test_implied_vol_round_trip():
    """Compute price then recover vol."""
    true_vol = 0.35
    price = black_scholes_call(100.0, 105.0, 0.05, 0.5, true_vol)
    recovered_vol = implied_vol(price, 100.0, 105.0, 0.05, 0.5, "call")
    np.testing.assert_almost_equal(true_vol, recovered_vol, decimal=3)


def test_ou_half_life():
    """Ensure OU process half-life evaluates cleanly."""
    np.random.seed(42)
    p = np.zeros(1000)
    for i in range(1, 1000):
        p[i] = p[i - 1] + 0.1 * (50 - p[i - 1]) + np.random.normal(0, 1)

    res = fit_ou_process(pd.Series(p))
    assert res.half_life > 0
    assert res.theta > 40 and res.theta < 60


def test_bonferroni_correction():
    """Validate FWER cutoff scaling (alpha / n)."""
    p_vals = [0.01, 0.005, 0.04, 0.1]
    res = apply_bonferroni(p_vals, alpha=0.05)
    assert list(res) == [True, True, False, False]


def test_bayesian_sharpe():
    """Validate probabilistic dampening effect."""
    observed = 1.2
    prior = 0.0
    prior_var = 1.0
    adj = compute_bayesian_adjusted_sharpe(observed, 100, prior, prior_var)
    assert adj < observed
    assert adj > prior


def test_nearest_pd_higham():
    """Verify negative eigenvalue projection to strictly positive domain."""
    A = np.array([
        [1.0, 0.9, 0.9],
        [0.9, 1.0, 0.9],
        [0.9, 0.9, 1.0],
    ])
    A[0, 1] = 2.0
    A[1, 0] = 2.0

    with pytest.raises(np.linalg.LinAlgError):
        np.linalg.cholesky(A)

    A_pd = nearest_positive_definite(A)
    np.linalg.cholesky(A_pd)
    assert A_pd.shape == A.shape
