"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from backend.agents.hypothesis_engine import HypothesisObject
from backend.math_engine.time_series import (
    run_adf_test, fit_arima, fit_garch_family, detect_vol_regimes, run_fft_analysis, run_wavelet_analysis
)
from backend.math_engine.cross_sectional import run_ff5_regression, run_rolling_alpha, run_pca
from backend.math_engine.portfolio import compute_calmar_ratio, compute_max_drawdown
from backend.math_engine.hypothesis_tests import (
    run_t_test, run_bootstrap_sharpe, apply_bonferroni, apply_benjamini_hochberg, compute_bayesian_adjusted_sharpe
)

logger = logging.getLogger(__name__)


@dataclass
class PerformanceReport:
    cagr: float
    cagr_survivorship_adj: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    
        
        
        
    # Advanced metrics
    bayes_sharpe: float
    bootstrap_p_value: float
    ff5_alpha: float
    ff5_r_squared: float
    garch_persistence: float
    
        
        
        
    # Sensitivity
    net_cagr_2bps: float
    net_cagr_10bps: float
    
        
        
        
    # Metadata context
    raw_results_dict: Dict[str, Any] = field(default_factory=dict)


class PerformanceCalculator:
    """master class running all 18 mathematical models over backtest output lol"""

    def __init__(self):
                                # Survivorship bias annual penalties
        self.SURVIVORSHIP_PREMIUM = {
            "large_cap": 0.005,
            "mid_cap": 0.015,
            "small_cap": 0.020,
            "default": 0.010
        }

    def compute_all(
        self,
        strategy_returns: pd.Series,
        benchmark_returns: pd.Series,
        rf_rate: float,
        ff5_factors: pd.DataFrame,
        garch_cond_vol: pd.Series,
        regime_series: pd.Series,
        sentiment_factor: Optional[pd.Series],
        hypothesis: HypothesisObject,
        prior_literature_sharpe: Optional[float]
    ) -> PerformanceReport:
        """computes the full 18-metric suite required for the reporting stage lol"""
        df = strategy_returns.dropna()
        if len(df) < 30:
            logger.warning("Strategy return series too short for full compute.")
            return PerformanceReport(0,0,0,0,0,0,0,0,0,0,0,0,0,0,0)

        
        
        
        # Basic Return/Vol
        years = len(df) / 252
        cum_ret = (1 + df).prod() - 1
        cagr = (1 + cum_ret) ** (1 / years) - 1 if years > 0 else 0.0
        
        vol_ann = df.std() * np.sqrt(252)
        excess_returns = df - rf_rate
        
        sharpe = (excess_returns.mean() / excess_returns.std() * np.sqrt(252)) if excess_returns.std() > 0 else 0.0
        
        downside = excess_returns[excess_returns < 0]
        sortino = (excess_returns.mean() / downside.std() * np.sqrt(252)) if len(downside) > 0 and downside.std() > 0 else 0.0
        
        win_rate = (df > 0).mean()
        
                
                
                
        # Drawdowns & Calmar
        calmar = compute_calmar_ratio(df)
        dd_res = compute_max_drawdown(df)
        
                
                
                
        # Hypothesis Testing
                                # 1. Bootstrap Sharpe
        boot_res = run_bootstrap_sharpe(df, n_bootstrap=2000)
        
                
                
                
        # 2. Bayesian Sharpe
        prior_mean = prior_literature_sharpe if prior_literature_sharpe is not None else 0.5
        bayes_sr = compute_bayesian_adjusted_sharpe(
            sample_sharpe=sharpe,
            n_periods=len(df),
            prior_mean=prior_mean,
            prior_std=0.5
        )
        
                
                
                
        # Cross-Sectional
        ff5_res = run_ff5_regression(df, ff5_factors)
        ff5_alpha = ff5_res.alpha if ff5_res else 0.0
        ff5_r_squared = ff5_res.r_squared if ff5_res else 0.0
        
                
                
                
        # Volatility / Time Series proxy
        garch_res = fit_garch_family(df)
        garch_pers = garch_res.persistence if garch_res else 0.0
        
                
                
                
        # --- Survivorship Bias Correction ---
        scope = (hypothesis.scope or "").lower()
        if "large" in scope:
            surv_penalty = self.SURVIVORSHIP_PREMIUM["large_cap"]
        elif "small" in scope:
            surv_penalty = self.SURVIVORSHIP_PREMIUM["small_cap"]
        elif "mid" in scope:
            surv_penalty = self.SURVIVORSHIP_PREMIUM["mid_cap"]
        else:
            surv_penalty = self.SURVIVORSHIP_PREMIUM["default"]
            
        cagr_adj = cagr - surv_penalty
        
                
                
                
        # --- Transaction Cost Sensitivity ---
                                # Assuming a default turnover of 10% of portfolio daily (0.1 trades/day) 
                                # strategy_returns - n_trades * cost_per_trade
                                # Annualized cost = 252 * turnover * bps
        turnover_daily = 0.10
        cost_2bps_daily = turnover_daily * 0.0002
        cost_10bps_daily = turnover_daily * 0.0010
        
        net_ret_2bps = df - cost_2bps_daily
        net_ret_10bps = df - cost_10bps_daily
        
        cagr_2bps = (1 + ((1 + net_ret_2bps).prod() - 1)) ** (1 / max(years, 1e-4)) - 1
        cagr_10bps = (1 + ((1 + net_ret_10bps).prod() - 1)) ** (1 / max(years, 1e-4)) - 1

        
        
        
        # Build raw dict for report formatting
        raw_stats = {
            "t_test": run_t_test(df),
            "bootstrap": boot_res,
            "ff5": ff5_res,
            "garch": garch_res
        }

        return PerformanceReport(
            cagr=float(cagr),
            cagr_survivorship_adj=float(cagr_adj),
            volatility=float(vol_ann),
            sharpe_ratio=float(sharpe),
            sortino_ratio=float(sortino),
            max_drawdown=float(dd_res.max_drawdown),
            calmar_ratio=float(calmar),
            win_rate=float(win_rate),
            bayes_sharpe=float(bayes_sr),
            bootstrap_p_value=float(boot_res.p_value_vs_zero),
            ff5_alpha=float(ff5_alpha),
            ff5_r_squared=float(ff5_r_squared),
            garch_persistence=float(garch_pers),
            net_cagr_2bps=float(cagr_2bps),
            net_cagr_10bps=float(cagr_10bps),
            raw_results_dict=raw_stats
        )
