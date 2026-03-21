"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from scipy.stats import norm

logger = logging.getLogger(__name__)


# --- Dataclasses ---

@dataclass
class GBMParams:
    mu: float
    sigma: float

@dataclass
class MertonParams:
    lambda_j: float  # Jumps per year
    mu_j: float      # Mean jump size
    sigma_j: float   # Std of jump size

@dataclass
class OUParams:
    kappa: float
    theta: float
    sigma_ou: float
    half_life: float




# --- Fitting ---

def fit_gbm(prices: pd.Series, dt: float = 1/252) -> Optional[GBMParams]:
    """maximum likelihood estimation of gbm parameters from daily prices lol"""
    if len(prices) < 2 or prices.iloc[-1] <= 0:
        return None

    try:
        log_returns = np.log(prices / prices.shift(1)).dropna()
        mu_iter = log_returns.mean() / dt
        sigma_iter = log_returns.std() / np.sqrt(dt)
        
                
        # Correct drift for Itô's Lemma: true mu = sample drift + 0.5*sigma^2
        mu_true = mu_iter + 0.5 * sigma_iter**2
        
        return GBMParams(mu=mu_true, sigma=sigma_iter)
    except Exception as e:
        logger.error("Failed to fit GBM: %s", e)
        return None

def fit_merton_jumps(returns: pd.Series, cond_vol: pd.Series, dt: float = 1/252) -> Optional[MertonParams]:
    """identifies and models jumps based on a 3-sigma conditional volatility threshold lol"""
    df = pd.concat([returns, cond_vol], axis=1).dropna()
    if len(df) < 50:
        return None

    try:
        R = df.iloc[:, 0]
                # Using 3 * scaled conditional volatility
        vol = df.iloc[:, 1]
        
                
        # Determine jump days
        is_jump = np.abs(R) > (3 * vol)
        jump_returns = R[is_jump]
        
        years = len(returns) * dt
        jump_count = len(jump_returns)
        
        lambda_j = jump_count / years if years > 0 else 0.0
        
        if jump_count >= 2:
            mu_j = jump_returns.mean()
            sigma_j = jump_returns.std()
        elif jump_count == 1:
            mu_j = jump_returns.iloc[0]
            sigma_j = 0.01  # Default small variance
        else:
            mu_j = 0.0
            sigma_j = 0.0
            
        return MertonParams(lambda_j=lambda_j, mu_j=mu_j, sigma_j=sigma_j)
    except Exception as e:
        logger.error("Failed to fit Merton jumps: %s", e)
        return None

def fit_ou_process(spread: pd.Series, dt: float = 1/252) -> Optional[OUParams]:
    """Fits an Ornstein-Uhlenbeck process (mean-reversion) via discrete OLS.
    
    Model: dX_t = kappa * (theta - X_t) * dt + sigma * dW_t
    OLS: Delta X_t = alpha + beta * X_{t-1} + epsilon
    """
    if len(spread) < 30:
        return None

    try:
        X = spread.dropna().values
        X_t = X[1:]
        X_t_minus_1 = X[:-1]
        
                
        # OLS regression
        A = np.vstack([np.ones_like(X_t_minus_1), X_t_minus_1]).T
        res = np.linalg.lstsq(A, X_t - X_t_minus_1, rcond=None)
        alpha, beta = res[0]
        residuals = (X_t - X_t_minus_1) - (alpha + beta * X_t_minus_1)
        
                
        # Catch non-mean-reverting scenarios
        if beta >= 0 or beta <= -1:
            logger.debug("OU fit implies non-stationary or diverging path (beta=%.4f).", beta)
            return None
            
        kappa = -np.log(1 + beta) / dt
        theta = -alpha / beta
        
                
        # Sigma derived from discrete error variance
        var_eps = np.var(residuals, ddof=1)
        sigma_ou = np.sqrt(var_eps / ((1 - np.exp(-2 * kappa * dt)) / (2 * kappa)))
        
        half_life = np.log(2) / kappa if kappa > 0 else np.inf
        
        return OUParams(kappa=kappa, theta=theta, sigma_ou=sigma_ou, half_life=half_life)
    except Exception as e:
        logger.error("Failed to fit OU process: %s", e)
        return None




# --- Simulation ---

def simulate_gbm_paths(params: GBMParams, n_paths: int, n_steps: int, dt: float = 1/252) -> np.ndarray:
    """generates an array of n_paths x n_steps standard gbm asset price paths lol"""
    try:
                # standard normal shocks
        Z = np.random.standard_normal((n_paths, n_steps))
        
        drift = (params.mu - 0.5 * params.sigma**2) * dt
        diffusion = params.sigma * np.sqrt(dt) * Z
        
                
        # S(t+1) = S(t) * exp(drift + diffusion)
                # We model log-returns to compute cumsum efficiently, starting at S(0)=1.0
        log_increments = drift + diffusion
        log_paths = np.cumsum(log_increments, axis=1)
        
        paths = np.exp(log_paths)
                # Prepend initial state 1.0
        start = np.ones((n_paths, 1))
        return np.hstack((start, paths))
    except Exception as e:
        logger.error("simulate_gbm_paths failed: %s", e)
        return np.zeros((0,0))

def simulate_merton_paths(
    merton: MertonParams, gbm: GBMParams, n_paths: int, n_steps: int, dt: float = 1/252
) -> np.ndarray:
    """generates an array of paths under the merton jump-diffusion model lol"""
    try:
        Z = np.random.standard_normal((n_paths, n_steps))
        
                
        # Poisson jump process
                # Expect lambda_j * dt jumps per step.
        poi_probs = merton.lambda_j * dt
                # Random matrix determining if a jump occurs (0 or 1 approximate for small dt)
        jumps = np.random.binomial(n=1, p=poi_probs, size=(n_paths, n_steps))
        
                
        # Jump sizes N(mu_j, sigma_j^2)
        jump_sizes = np.random.normal(merton.mu_j, merton.sigma_j, size=(n_paths, n_steps))
        
                
        # Merton compensator to maintain neutral drift expectations
        k_bar = np.exp(merton.mu_j + 0.5 * merton.sigma_j**2) - 1
        
        drift = (gbm.mu - merton.lambda_j * k_bar - 0.5 * gbm.sigma**2) * dt
        diffusion = gbm.sigma * np.sqrt(dt) * Z
        
        log_increments = drift + diffusion + (jumps * jump_sizes)
        log_paths = np.cumsum(log_increments, axis=1)
        
        paths = np.exp(log_paths)
        start = np.ones((n_paths, 1))
        return np.hstack((start, paths))
    except Exception as e:
        logger.error("simulate_merton_paths failed: %s", e)
        return np.zeros((0,0))

def _nearest_pd(A: np.ndarray) -> np.ndarray:
    """finds the nearest positive-definite matrix to input a (higham 1988) lol"""
    B = (A + A.T) / 2
    _, s, V = np.linalg.svd(B)
    H = np.dot(V.T, np.dot(np.diag(s), V))
    A2 = (B + H) / 2
    A3 = (A2 + A2.T) / 2
    
        
    # Check if PD
    if _is_pd(A3):
        return A3
        
    spacing = np.spacing(np.linalg.norm(A))
    I = np.eye(A.shape[0])
    k = 1
    while not _is_pd(A3):
        mineig = np.min(np.real(np.linalg.eigvals(A3)))
        A3 += I * (-mineig * k**2 + spacing)
        k += 1
    return A3

def _is_pd(B: np.ndarray) -> bool:
    """checks if a matrix is positive definite via cholesky decomposition lol"""
    try:
        np.linalg.cholesky(B)
        return True
    except np.linalg.LinAlgError:
        return False

def compute_correlated_paths(
    cov_matrix: np.ndarray, means: np.ndarray, n_paths: int, n_steps: int, dt: float = 1/252
) -> np.ndarray:
    """generates correlated multivariate random walks via cholesky decomposition lol"""
    n_assets = len(means)
    
        
    # Ensure covariance matrix is positive definite
    if not _is_pd(cov_matrix):
        cov_matrix = _nearest_pd(cov_matrix)
        
    try:
        L = np.linalg.cholesky(cov_matrix)
        
                
        # We need independent standards: shape (n_paths, n_steps, n_assets)
        Z = np.random.standard_normal((n_paths, n_steps, n_assets))
        
                
        # Transform to correlated steps: Z_corr = Z * L^T  (broadcasted)
                # Using tensordot or einsum for clarity
        Z_corr = np.einsum('psa, ab -> psb', Z, L.T)
        
        paths = np.zeros((n_paths, n_steps + 1, n_assets))
        paths[:, 0, :] = 1.0  # Initialised to price 1.0 
        
                
        # S(t+1) = S(t) * exp( (mu - sigma^2/2)dt + Z_corr * sqrt(dt) )
        sigs2 = np.diag(cov_matrix)
        drift = (means - 0.5 * sigs2) * dt
        
        log_incs = drift + Z_corr * np.sqrt(dt)
        log_paths = np.cumsum(log_incs, axis=1)
        
        paths[:, 1:, :] = np.exp(log_paths)
        return paths
    except Exception as e:
        logger.error("compute_correlated_paths failed: %s", e)
        return np.zeros((0,0,0))
