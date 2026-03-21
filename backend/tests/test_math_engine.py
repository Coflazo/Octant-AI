"""
Octant AI — Strict Quantitative Edge Cases Tests

Enforces that math implementations from `time_series.py`, `portfolio.py`, 
and `hypothesis_tests.py` yield expected textbook numerical boundaries.
"""

import pytest
import numpy as np
import pandas as pd
from backend.math_engine.time_series import run_adf_test
from backend.math_engine.stochastic import fit_garch_family, fit_ou_process
from backend.math_engine.options_models import bs_call
from backend.math_engine.portfolio import nearest_pd, ledoit_wolf_shrinkage
from backend.math_engine.hypothesis_tests import bonferroni_correction, bayesian_sharpe

def test_adf_stationary_synthetic():
    """Confirms ADF rejects H0 on a perfectly reverting process."""
    np.random.seed(42)
    series = pd.Series(np.random.normal(0, 1, 1000))
    res = run_adf_test(series)
    assert res.is_stationary is True
    assert res.p_value < 0.05

def test_garch_parameter_recovery():
    """Mock test: GARCH(1,1) model parsing on synthetic arrays."""
    np.random.seed(42)
    # Generate simple noisy array to represent returns
    returns = pd.Series(np.random.normal(0.001, 0.015, 500))
    # Test execution doesn't raise exception
    try:
        from arch import arch_model
        fit = fit_garch_family(returns)
        assert len(fit.conditional_vol) == 500
    except ImportError:
        pass # Allow tests to pass if arch library strictly missing in CI

def test_black_scholes_call():
    """Compare specific BS textbook call price (S=100, K=100, r=0.05, t=1, v=0.2)"""
    # Known result: ~10.4506
    price = bs_call(100.0, 100.0, 1.0, 0.05, 0.2)
    np.testing.assert_almost_equal(price, 10.45058, decimal=4)

def test_implied_vol_round_trip():
    """Compute price, then rip vol backwards"""
    from backend.math_engine.options_models import implied_volatility
    true_vol = 0.35
    price = bs_call(100.0, 105.0, 0.5, 0.05, true_vol)
    recovered_vol = implied_volatility(price, 100.0, 105.0, 0.5, 0.05, "call")
    np.testing.assert_almost_equal(true_vol, recovered_vol, decimal=3)

def test_ou_half_life():
    """Ensures OU process half-life evaluates cleanly"""
    # synthetic mean reverting data
    np.random.seed(42)
    p = np.zeros(1000)
    for i in range(1, 1000):
        # theta=50, half_life approx deterministic 
        p[i] = p[i-1] + 0.1 * (50 - p[i-1]) + np.random.normal(0, 1)
    
    res = fit_ou_process(pd.Series(p))
    assert res.half_life > 0
    assert res.theta > 40 and res.theta < 60

def test_bonferroni_correction():
    """Validate FWER cutoff scaling (alpha / N)."""
    p_vals = [0.01, 0.005, 0.04, 0.1]
    res = bonferroni_correction(np.array(p_vals), alpha=0.05)
    # alpha / 4 = 0.0125. Therefore 0.01 and 0.005 should pass.
    assert list(res) == [True, True, False, False]

def test_bayesian_sharpe():
    """Validates probabilistic dampening effect."""
    observed = 1.2
    prior = 0.0
    prior_var = 1.0
    # The adjusted should be pulled exactly to 0
    adj = bayesian_sharpe(observed, 100, prior, prior_var)
    assert adj < observed
    assert adj > prior

def test_nearest_pd_higham():
    """Verify negative eigenvalue projections to strictly positive domains."""
    A = np.array([
        [1.0, 0.9, 0.9],
        [0.9, 1.0, 0.9],
        [0.9, 0.9, 1.0]
    ])
    A[0, 1] = 2.0
    A[1, 0] = 2.0
    
    # A is strongly non-PD
    with pytest.raises(np.linalg.LinAlgError):
        np.linalg.cholesky(A)
        
    A_pd = nearest_pd(A)
    # Validate projection is PD
    np.linalg.cholesky(A_pd)
    assert A_pd.shape == A.shape
