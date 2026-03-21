"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import norm
import statsmodels.api as sm

try:
    from sklearn.decomposition import PCA
except ImportError:
    pass

logger = logging.getLogger(__name__)


# --- Dataclasses ---

@dataclass
class FF5RegressionResult:
    alpha: float
    alpha_t_stat: float
    betas: Dict[str, float]
    beta_t_stats: Dict[str, float]
    r_squared: float
    residuals: pd.Series

@dataclass
class RollingAlphaResult:
    alpha_series: pd.Series
    rolling_sharpe: pd.Series
    alpha_decay_flag: bool

@dataclass
class PCAResult:
    loadings: pd.DataFrame
    explained_variance: np.ndarray
    eigenvalues: np.ndarray
    marchenko_pastur_max: float
    significant_pcs: int
    is_signal: List[bool]




# --- Functions ---

def run_ff5_regression(strategy_returns: pd.Series, ff5_factors: pd.DataFrame) -> Optional[FF5RegressionResult]:
    """runs ols ff5 regression with newey-west hac standard errors lol"""
    try:
                # Align dates
        df = pd.concat([strategy_returns, ff5_factors], axis=1).dropna()
        if len(df) < 30:
            return None

        y = df.iloc[:, 0]
        X = df.iloc[:, 1:]
        X = sm.add_constant(X)
        
                
        # Newey-West lag heuristic: floor(4 * (T/100)^(2/9))
        T = len(df)
        max_lags = int(np.floor(4 * (T / 100)**(2/9)))
        
        model = sm.OLS(y, X)
        results = model.fit(cov_type='HAC', cov_kwds={'maxlags': max_lags})
        
        alpha = results.params.get('const', 0.0)
        alpha_t = results.tvalues.get('const', 0.0)
        
        betas = {col: results.params[col] for col in X.columns if col != 'const'}
        beta_t = {col: results.tvalues[col] for col in X.columns if col != 'const'}
        
        return FF5RegressionResult(
            alpha=alpha,
            alpha_t_stat=alpha_t,
            betas=betas,
            beta_t_stats=beta_t,
            r_squared=results.rsquared,
            residuals=results.resid
        )
    except Exception as e:
        logger.error("Failed to run FF5 regression: %s", e)
        return None

def run_rolling_alpha(strategy_returns: pd.Series, ff5_factors: pd.DataFrame, window_months: int = 12) -> Optional[RollingAlphaResult]:
    """computes rolling alpha via 12-month rolling ols regressions lol"""
    window_days = window_months * 21
    df = pd.concat([strategy_returns, ff5_factors], axis=1).dropna()
    
    if len(df) <= window_days:
        return None

    alphas = []
    dates = []
    
    try:
        y_all = df.iloc[:, 0]
        X_all = sm.add_constant(df.iloc[:, 1:])
        
                
        # Rolling regression
        for i in range(window_days, len(df)):
            y_win = y_all.iloc[i-window_days:i]
            X_win = X_all.iloc[i-window_days:i, :]
            
                        
            # fast fit, no HAC needed per window unless requested
            try:
                res = sm.OLS(y_win, X_win).fit()
                alphas.append(res.params['const'])
                dates.append(df.index[i])
            except:
                alphas.append(0.0)
                dates.append(df.index[i])
                
        alpha_series = pd.Series(alphas, index=dates)
        
                
        # Rolling Sharpe of the Alpha Series
                # SR_alpha = avg(alpha) / std(alpha) * sqrt(252)
        roll_alpha_mean = alpha_series.rolling(window_days).mean()
        roll_alpha_std = alpha_series.rolling(window_days).std()
        
        roll_sharpe = (roll_alpha_mean / roll_alpha_std) * np.sqrt(252)
        
                
        # Simple heuristic to flag decay: recent 3m alpha < avg 12m alpha - 1 stdev
        alpha_decay = False
        if len(alpha_series) > 63:
            recent_mean = alpha_series.iloc[-63:].mean()
            hist_mean = alpha_series.mean()
            hist_std = alpha_series.std()
            if recent_mean < (hist_mean - hist_std):
                alpha_decay = True

        return RollingAlphaResult(
            alpha_series=alpha_series,
            rolling_sharpe=roll_sharpe,
            alpha_decay_flag=alpha_decay
        )
            
    except Exception as e:
        logger.error("Failed to compute rolling alpha: %s", e)
        return None


def detect_marchenko_pastur_noise(eigenvalues: np.ndarray, n_assets: int, n_periods: int) -> Tuple[List[bool], float]:
    """Identifies which eigenvalues fall outside the Marchenko-Pastur distribution noise band.
    True = signal, False = noise.
    
    Returns:
        is_signal_list, mp_max_boundary
    """
    if n_periods <= 0 or n_assets <= 0:
        return [False for _ in eigenvalues], 0.0
        
    q = n_assets / n_periods
    if q > 1:
                # q should ideally be < 1, but PCA can still be computed.
                # Handling T < N by bounding q.
        pass
        
            
    # Assume sigma^2 = 1.0 since PCA operates on standardized correlation matrices
        # Alternatively estimate sigma^2 from the median eigenvalue 
    sigma_sq = 1.0 
    
    lambda_max = sigma_sq * (1 + np.sqrt(q))**2
    lambda_min = sigma_sq * (1 - np.sqrt(q))**2
    
    is_signal = [float(e) > lambda_max for e in eigenvalues]
    return is_signal, lambda_max


def run_pca(return_matrix: pd.DataFrame) -> Optional[PCAResult]:
    """runs sklearn pca and isolates meaningful factors using marchenko-pastur lol"""
    df = return_matrix.dropna()
    N = df.shape[1]
    T = df.shape[0]
    
    if N < 2 or T < 10:
        return None

    try:
                # Standardize returns
        rets_norm = (df - df.mean()) / df.std()
        
        pca = PCA()
        pca.fit(rets_norm)
        
        eigenvals = pca.explained_variance_
        variance_ratio = pca.explained_variance_ratio_
        loadings = pd.DataFrame(pca.components_.T, index=df.columns, columns=[f"PC{i+1}" for i in range(N)])
        
        is_signal, mp_max = detect_marchenko_pastur_noise(eigenvals, N, T)
        significant_pcs = sum(is_signal)
        
        return PCAResult(
            loadings=loadings,
            explained_variance=variance_ratio,
            eigenvalues=eigenvals,
            marchenko_pastur_max=mp_max,
            significant_pcs=significant_pcs,
            is_signal=is_signal
        )
    except Exception as e:
        logger.error("PCA decomposition failed: %s", e)
        return None
