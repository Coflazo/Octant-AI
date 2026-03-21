"""
Octant AI — Math Engine: Hypothesis Tests

Enforces academic rigor via Bootstrapped Sharpe Ratios, Bayes-Adjusted Sharpe,
and p-value correction frameworks (Bonferroni / Benjamini-Hochberg) to prevent
multiple comparison bias across concurrent trading model searches.
"""

import logging
from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

# --- Dataclasses ---

@dataclass
class TTestResult:
    t_stat: float
    df: int
    p_value_two_tailed: float
    p_value_one_tailed: float

@dataclass
class BootstrapResult:
    sharpe_mean: float
    confidence_interval_95: tuple[float, float]
    p_value_vs_zero: float


# --- Core Algorithms ---

def run_t_test(returns: pd.Series) -> TTestResult:
    """Computes basic one-sided and two-sided t-stats over strategy returns."""
    rets = returns.dropna()
    N = len(rets)
    if N < 2 or rets.std() == 0:
        return TTestResult(0.0, 0, 1.0, 1.0)
        
    mean = rets.mean()
    std = rets.std()
    sq_n = np.sqrt(N)
    
    t_stat = (mean / (std / sq_n)) 
    df = N - 1
    
    p_two = 1.0
    p_one = 1.0
    if not np.isnan(t_stat):
        p_two = float(2 * (1 - stats.t.cdf(abs(t_stat), df)))
        p_one = float(1 - stats.t.cdf(t_stat, df)) if t_stat > 0 else float(stats.t.cdf(t_stat, df))

    return TTestResult(t_stat=float(t_stat), df=int(df), p_value_two_tailed=p_two, p_value_one_tailed=p_one)


def run_bootstrap_sharpe(returns: pd.Series, n_bootstrap: int = 10000) -> BootstrapResult:
    """Non-parametric block sampling with replacement to test Sharpe distribution."""
    rets = returns.dropna().values
    N = len(rets)
    if N < 30:
        return BootstrapResult(0.0, (0.0, 0.0), 1.0)
        
    obs_mean = np.mean(rets)
    obs_std = np.std(rets, ddof=1)
    if obs_std == 0:
        return BootstrapResult(0.0, (0.0, 0.0), 1.0)
        
    obs_sharpe = (obs_mean / obs_std) * np.sqrt(252)
    
    # We enforce the null hypothesis that true mean return = 0 by centering the distribution
    centered_rets = rets - obs_mean
    
    # Bootstrapping
    # Generating indices mapping array
    indices = np.random.randint(0, N, size=(n_bootstrap, N))
    sampled = centered_rets[indices]
    
    means = np.mean(sampled, axis=1)
    stds = np.std(sampled, axis=1, ddof=1)
    
    # Handle zero-std paths to avoid division by zero
    stds[stds == 0] = 1e-8
    null_sharpes = (means / stds) * np.sqrt(252)
    
    # P-value = fraction of null sharpes matching or exceeding our observed
    p_val = np.sum(null_sharpes >= obs_sharpe) / n_bootstrap
    
    # Get 95% CI of the ACTUALLY observed distribution (from non-centered sampling)
    real_sampled = rets[indices]
    real_means = np.mean(real_sampled, axis=1)
    real_stds = np.std(real_sampled, axis=1, ddof=1)
    real_stds[real_stds == 0] = 1e-8
    real_sharpes = (real_means / real_stds) * np.sqrt(252)
    
    lower = np.percentile(real_sharpes, 2.5)
    upper = np.percentile(real_sharpes, 97.5)
    
    return BootstrapResult(
        sharpe_mean=float(np.mean(real_sharpes)),
        confidence_interval_95=(float(lower), float(upper)),
        p_value_vs_zero=float(p_val)
    )

def apply_bonferroni(p_values: List[float], alpha: float = 0.05) -> List[bool]:
    """Strict Family-Wise Error Rate control."""
    N = len(p_values)
    if N == 0: return []
    threshold = alpha / N
    return [p <= threshold for p in p_values]

def apply_benjamini_hochberg(p_values: List[float], alpha: float = 0.05) -> List[bool]:
    """False Discovery Rate (FDR) control via classical step-up procedure."""
    N = len(p_values)
    if N == 0: return []
    
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]
    
    thresholds = (np.arange(1, N + 1) / N) * alpha
    
    # Find the largest k where p_k <= (k/N)*alpha
    k = 0
    for i in range(N - 1, -1, -1):
        if sorted_p[i] <= thresholds[i]:
            k = i + 1
            break
            
    is_sig = [False] * N
    for i in range(k):
        is_sig[sorted_indices[i]] = True
        
    return is_sig

def compute_bayesian_adjusted_sharpe(sample_sharpe: float, n_periods: int, prior_mean: float = 0.5, prior_std: float = 0.5) -> float:
    """Calculates Bayesian Sharpe using standard Normal-Normal conjugate.
    Normalizes excessive short-series variance.
    """
    if n_periods == 0: return prior_mean
    
    # Precision is 1/variance
    prior_prec = 1.0 / (prior_std**2)
    
    # In standard SR approximations, variance error ≈ 1/n_periods
    likelihood_prec = n_periods / 1.0 # assumes variance scalar = 1
    
    post_prec = prior_prec + likelihood_prec
    post_mean = (prior_prec * prior_mean + likelihood_prec * sample_sharpe) / post_prec
    
    return float(post_mean)

def label_significance(bonferroni_pass: bool, bh_pass: bool) -> str:
    """Helper to convert FWER and FDR indicators to string labels."""
    if bonferroni_pass:
        return "strongly significant"
    elif bh_pass:
        return "significant"
    else:
        return "not significant"
