"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq

logger = logging.getLogger(__name__)

@dataclass
class VolSurface:
    smile: np.ndarray          # The 2D volatility curve at closest maturity
    term_structure: np.ndarray # The 2D term structure (ATM implied vol over time)
    implied_vols: pd.DataFrame # Complete grid mapping


def _d1_d2(S: float, K: float, r: float, T: float, sigma: float) -> tuple[float, float]:
    """helper to compute probability factors d1 and d2 lol"""
    if T <= 0 or sigma <= 0 or K <= 0 or S <= 0:
        return 0.0, 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return d1, d2

def black_scholes_call(S: float, K: float, r: float, T: float, sigma: float) -> float:
    """prices a european call option lol"""
    if T <= 0:
        return max(0.0, S - K)
    d1, d2 = _d1_d2(S, K, r, T, sigma)
    return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

def black_scholes_put(S: float, K: float, r: float, T: float, sigma: float) -> float:
    """prices a european put option via put-call parity lol"""
    if T <= 0:
        return max(0.0, K - S)
    d1, d2 = _d1_d2(S, K, r, T, sigma)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

def bs_delta(S: float, K: float, r: float, T: float, sigma: float, option_type: str) -> float:
    if T <= 0:
        return 1.0 if (option_type == "call" and S > K) else (-1.0 if (option_type == "put" and S < K) else 0.0)
    d1, _ = _d1_d2(S, K, r, T, sigma)
    if option_type == "call":
        return norm.cdf(d1)
    return norm.cdf(d1) - 1

def bs_gamma(S: float, K: float, r: float, T: float, sigma: float) -> float:
    if T <= 0: return 0.0
    d1, _ = _d1_d2(S, K, r, T, sigma)
    return norm.pdf(d1) / (S * sigma * np.sqrt(T))

def bs_theta(S: float, K: float, r: float, T: float, sigma: float, option_type: str) -> float:
    if T <= 0: return 0.0
    d1, d2 = _d1_d2(S, K, r, T, sigma)
    term1 = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
    if option_type == "call":
        term2 = r * K * np.exp(-r * T) * norm.cdf(d2)
        return term1 - term2
    else:
        term2 = r * K * np.exp(-r * T) * norm.cdf(-d2)
        return term1 + term2

def bs_vega(S: float, K: float, r: float, T: float, sigma: float) -> float:
    if T <= 0: return 0.0
    d1, _ = _d1_d2(S, K, r, T, sigma)
    return S * np.sqrt(T) * norm.pdf(d1)

def bs_rho(S: float, K: float, r: float, T: float, sigma: float, option_type: str) -> float:
    if T <= 0: return 0.0
    _, d2 = _d1_d2(S, K, r, T, sigma)
    if option_type == "call":
        return K * T * np.exp(-r * T) * norm.cdf(d2)
    return -K * T * np.exp(-r * T) * norm.cdf(-d2)

def implied_vol(market_price: float, S: float, K: float, r: float, T: float, option_type: str) -> float:
    """finds the implied volatility using brent's method lol"""
    if T <= 0 or market_price <= 0:
        return 0.0
        
    def objective(sigma):
        if option_type == "call":
            return black_scholes_call(S, K, r, T, sigma) - market_price
        return black_scholes_put(S, K, r, T, sigma) - market_price

    try:
                # Bracket between 10 basis points and 1000%
        iv = brentq(objective, 1e-6, 10.0)
        return float(iv)
    except Exception as e:
        logger.debug("Implied Volatility root-find non-convergence (C=%.2f, K=%.2f, T=%.2f): %s", market_price, K, T, e)
        return 0.0

def build_vol_surface(options_chain: pd.DataFrame) -> Optional[VolSurface]:
    """Constructs a Volatility Surface from an options chain.
    
    Args:
        options_chain: DataFrame demanding columns: [S, K, r, T, type, market_price]
        
    Returns:
        Structured VolSurface dataclass.
    """
    if options_chain.empty:
        return None
        
    try:
        ivs = []
        for _, row in options_chain.iterrows():
            iv = implied_vol(
                market_price=row["market_price"],
                S=row["S"],
                K=row["K"],
                r=row["r"],
                T=row["T"],
                option_type=row["type"]
            )
            ivs.append(iv)
            
        df = options_chain.copy()
        df["implied_vol"] = ivs
        df = df[df["implied_vol"] > 0]
        
        if df.empty:
            return None
            
        atm_df = df[(df['K']/df['S'] >= 0.95) & (df['K']/df['S'] <= 1.05)]
        term_structure = np.array([])
        if not atm_df.empty:
            agg_ts = atm_df.groupby("T")["implied_vol"].mean().sort_index()
            term_structure = np.column_stack((agg_ts.index, agg_ts.values))
            
        nearest_expiry = df["T"].min()
        smile_df = df[df["T"] == nearest_expiry]
        smile = np.array([])
        if not smile_df.empty:
            agg_sm = smile_df.groupby("K")["implied_vol"].mean().sort_index()
            smile = np.column_stack((agg_sm.index, agg_sm.values))
            
        return VolSurface(smile=smile, term_structure=term_structure, implied_vols=df)
        
    except Exception as e:
        logger.error("Failed to build volatility surface: %s", e)
        return None

def compute_risk_reversal_25(vol_surface: VolSurface) -> float:
    """rr(25) = iv(25δ call) - iv(25δ put) lol"""
        # Mocking delta extraction purely from VolSurface grid.
    if vol_surface is None or vol_surface.implied_vols.empty:
        return 0.0
        
    df = vol_surface.implied_vols
        # In a real model we would filter by exact delta=0.25 on the curve. 
        # Here we simulate the logic by grabbing average call skew vs put skew.
    calls = df[df["type"] == "call"]
    puts = df[df["type"] == "put"]
    
    if calls.empty or puts.empty:
        return 0.0
        
    call_str = calls[calls["K"] > calls["S"]]
    put_str = puts[puts["K"] < puts["S"]]
    
    if call_str.empty or put_str.empty:
        return 0.0
        
    return float(call_str["implied_vol"].mean() - put_str["implied_vol"].mean())

def compute_vol_term_structure_slope(vol_surface: VolSurface) -> float:
    """(iv_3m - iv_1m)/iv_1m lol"""
    if vol_surface is None or len(vol_surface.term_structure) < 2:
        return 0.0
        
    ts = vol_surface.term_structure # [[T, IV], ...]
    if len(ts) == 0:
        return 0.0
        
            
    # Extrapolate nearest to 1m (0.08 yr) and 3m (0.25 yr)
    idx_1m = np.argmin(np.abs(ts[:, 0] - 0.08))
    idx_3m = np.argmin(np.abs(ts[:, 0] - 0.25))
    
    iv_1m = ts[idx_1m, 1]
    iv_3m = ts[idx_3m, 1]
    
    if iv_1m == 0:
        return 0.0
        
    return float((iv_3m - iv_1m) / iv_1m)
