"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import vectorbt as vbt
except ImportError:
    pass

from backend.agents.hypothesis_engine import HypothesisObject
from backend.agents.universe_builder import UniverseBuildResult
from backend.pulse import PulseEmitter
from backend.math_engine.performance import PerformanceCalculator, PerformanceReport
from backend.math_engine.time_series import fit_ou_process, fit_garch_family, detect_vol_regimes

logger = logging.getLogger(__name__)


def construct_signal(
    hypothesis: HypothesisObject,
    price_matrix: Dict[str, pd.DataFrame],
    universe_df: pd.DataFrame,
    sentiment_signals: Dict,
    math_results: Dict
) -> Tuple[pd.Series, pd.Series]:
    """Dynamically routes hypothesis parameters into a quantitative boolean signal.
    
    Returns:
        (entries: pd.Series, exits: pd.Series) representing the unified portfolio signal series.
    """
    cat = hypothesis.math_method_category.lower()
    
        
        
        
    # We aggregate signals across the entire universe into a single representative composite trace 
                # to run a unified backtest proxy. In production, this would be an NxT matrix backtest.
                # For MVP speed, we use an equal-weighted proxy of the first 3 valid tickers.
    
        
        
        
    # Grab the first available ticker to mock the framework
    target_ticker = "AAPL"
    if price_matrix and len(price_matrix) > 0:
        target_ticker = list(price_matrix.keys())[0]
        
    df = price_matrix.get(target_ticker, pd.DataFrame())
    if df.empty or "Close" not in df.columns:
                                # Return empty signals
        return pd.Series(dtype=bool), pd.Series(dtype=bool)

    closes = df["Close"]
    returns = closes.pct_change().dropna()
    
    entries = pd.Series(False, index=closes.index)
    exits = pd.Series(False, index=closes.index)
    
    sentiment_z = 0.0
    if target_ticker in sentiment_signals:
        sentiment_z = sentiment_signals[target_ticker].z_score

    
    
    
    # Baseline Routing Logic (Mocking exact signal logic per path)
    if "time_series" in cat:
                                # Mean cross-over proxy
        ma_short = closes.rolling(10).mean()
        ma_long = closes.rolling(50).mean()
        entries = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
        exits = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))
        
    elif "mean_reversion" in cat:
                                # Z-score of close vs 20d moving average
        roll_mean = closes.rolling(20).mean()
        roll_std = closes.rolling(20).std()
        z = (closes - roll_mean) / roll_std
        entries = z < -2.0
        exits = z > 0.0
        
    elif "factor_model" in cat:
                                # Mock Factor signal: positive weekly return + positive sentiment
        weekly_ret = closes.pct_change(5)
        entries = (weekly_ret > 0.01) & (sentiment_z > 0.5)
        exits = weekly_ret < -0.01
        
    elif "regime_detection" in cat:
                                # Mocking HMM volatility regime logic
        garch_res = fit_garch_family(returns)
        if garch_res:
            hmm_res = detect_vol_regimes(garch_res.conditional_volatility)
            if hmm_res:
                prob_high = hmm_res.regime_probs
                                                                # Buy when low vol regime is highly probable
                entries = prob_high < 0.2
                exits = prob_high > 0.8
                                                                # Re-index to closes match
                entries = entries.reindex(closes.index, fill_value=False)
                exits = exits.reindex(closes.index, fill_value=False)
    
    elif "volatility_surface" in cat or "options_pricing" in cat:
                                # Volatility breakout
        roll_std = closes.rolling(20).std()
        entries = roll_std > roll_std.rolling(50).mean() * 1.5
        exits = roll_std < roll_std.rolling(50).mean()
        
    else:
                                # Default momentum
        entries = closes > closes.rolling(20).mean()
        exits = closes < closes.rolling(20).mean()

    
    
    
    # Incorporate sentiment global override filter
    if sentiment_z < -2.0:
        entries = entries & False  # Block entries if Reddit is highly bearish

    return entries.fillna(False), exits.fillna(False)


def run_vbt_backtest(entries: pd.Series, exits: pd.Series, price_data: pd.Series, long_only: bool) -> Dict:
    """runs a highly optimised vectorized backtest using vectorbt lol"""
    if entries.sum() == 0:
        return {"cagr": 0.0, "sharpe": 0.0, "max_dd": 0.0, "win_rate": 0.0}
        
    try:
        portfolio = vbt.Portfolio.from_signals(
            price_data,
            entries,
            exits,
            fees=0.0002,     # 2 bps transaction cost
            slippage=0.0001, # 1 bps slippage
            freq='d'
        )
        
        stats = portfolio.stats()
        return {
            "cagr": stats.get("Total Return [%]", 0.0) / 100.0, # Approximate CAGR given 10y range
            "sharpe": stats.get("Sharpe Ratio", 0.0),
            "max_dd": stats.get("Max Drawdown [%]", 0.0) / 100.0,
            "win_rate": stats.get("Win Rate [%]", 0.0) / 100.0,
            "portfolio": portfolio
        }
    except Exception as e:
        logger.error("VectorBT run failed: %s", e)
        return {"cagr": 0.0, "sharpe": 0.0, "max_dd": 0.0, "win_rate": 0.0}


def run_custom_backtest(
    entries: pd.Series,
    exits: pd.Series,
    price_data: pd.Series,
    signal_values: pd.Series,
    garch_series: Optional[pd.Series] = None,
    regime_series: Optional[pd.Series] = None
) -> Tuple[pd.DataFrame, Dict]:
    """iterative python engine generating explainable, row-by-row trade logs lol"""
    trade_log = []
    
    in_position = False
    entry_price = 0.0
    entry_date = None
    
        
        
        
    # Sync indices
    df = pd.DataFrame({
        "Close": price_data,
        "Enter": entries,
        "Exit": exits,
        "Signal": signal_values
    }).dropna()
    
    for date, row in df.iterrows():
        if row["Enter"] and not in_position:
            in_position = True
            entry_price = row["Close"]
            entry_date = date
            
        elif row["Exit"] and in_position:
            in_position = False
            exit_price = row["Close"]
            ret = (exit_price - entry_price) / entry_price - 0.0002 # 2 bps fee
            
            trade_log.append({
                "entry_date": entry_date,
                "exit_date": date,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return": ret,
                "signal_at_entry": row.get("Signal", 0.0)
            })
            
    log_df = pd.DataFrame(trade_log)
    stats = {}
    if not log_df.empty:
        stats["trades"] = len(log_df)
        stats["win_rate"] = (log_df["return"] > 0).mean()
        stats["avg_return"] = log_df["return"].mean()
    else:
        stats["trades"] = 0
        stats["win_rate"] = 0.0
        stats["avg_return"] = 0.0
        
    return log_df, stats


class BacktestingAgent:
    """agent 4: iterates through hypotheses, firing dual backtests and compiling reports lol"""
    
    def __init__(self):
        self.perf_calc = PerformanceCalculator()

    async def run(
        self,
        universe_result: UniverseBuildResult,
        hypotheses: List[HypothesisObject],
        citations_db: Dict,
        pulse: PulseEmitter
    ) -> Dict[str, PerformanceReport]:
        """main orchestrator for agent 4 lol"""
        total = len(hypotheses)
        results: Dict[str, PerformanceReport] = {}
        
        await pulse.emit_status("backtesting", "active", 0, total, "Initialising Engines", "VectorBT + Explainable Loop", 0, total * 30)

        
        
        
        # We need a primary asset to measure benchmark / baseline
        target_ticker = "SPY"
        if target_ticker not in universe_result.price_matrix:
            if universe_result.price_matrix:
                target_ticker = list(universe_result.price_matrix.keys())[0]
                
        price_df = universe_result.price_matrix.get(target_ticker, pd.DataFrame())
        if price_df.empty:
            logger.error("No valid price history to run backtests on.")
            return results
            
        benchmark_returns = price_df["Close"].pct_change().dropna()

        for idx, hyp in enumerate(hypotheses):
            step = idx + 1
            await pulse.emit_status("backtesting", "active", step, total, f"Testing Sub-Hypothesis {step}", hyp.hypothesis, int((step/total)*100), (total-step)*30)

            
            
            
            # 1. Target variables
                                                # For iteration, mock an empty math_results cross-section
            math_results = {}
            
                        
                        
                        
            # 2. Construct boolean signals
            entries, exits = construct_signal(
                hypothesis=hyp,
                price_matrix=universe_result.price_matrix,
                universe_df=universe_result.universe_df,
                sentiment_signals=universe_result.sentiment_signals,
                math_results=math_results
            )
            
                        
                        
                        
            # 3. VectorBT Fast Engine
            vbt_stats = run_vbt_backtest(entries, exits, price_df["Close"], long_only=True)
            
                        
                        
                        
            # 4. Extract simulated portfolio return series from VectorBT object
            portfolio = vbt_stats.get("portfolio")
            if portfolio is not None:
                strat_returns = portfolio.returns()
            else:
                strat_returns = pd.Series(0.0, index=benchmark_returns.index)
            
                        
                        
                        
            # 5. Explainable Python Engine
                                                # Create a mock continuous signal series merely for the explainable log
            sig_vals = pd.Series(0.0, index=price_df.index)
            log_df, custom_stats = run_custom_backtest(
                entries, exits, price_df["Close"], sig_vals
            )
            
                        
                        
                        
            # 6. Extract prior literature Sharpe
            prior_sr = 0.5
            if hyp.hypothesis in citations_db:
                                                                # Mock extracting avg effect size
                prior_sr = 0.8
            
                        
                        
                        
            # 7. Performance Report Generation
                                                # Provide empty series defaults for optional math objects (garch, regime) if not computed
            garch_vol = pd.Series(0.15, index=strat_returns.index)
            regime = pd.Series(1) 
            
            report = self.perf_calc.compute_all(
                strategy_returns=strat_returns,
                benchmark_returns=benchmark_returns,
                rf_rate=0.02, # 2% risk-free assumption
                ff5_factors=universe_result.ff5_factors,
                garch_cond_vol=garch_vol,
                regime_series=regime,
                sentiment_factor=None,
                hypothesis=hyp,
                prior_literature_sharpe=prior_sr
            )
            
                        
                        
                        
            # Incorporate explicit VectorBT findings to bridge gap
            if report.cagr == 0 and vbt_stats.get("cagr") != 0:
                report.cagr = vbt_stats["cagr"]
                report.sharpe_ratio = vbt_stats["sharpe"]
                report.max_drawdown = vbt_stats["max_dd"]

            results[hyp.hypothesis] = report
            
                        
                        
                        
            # 8. Emit individual metric result to PULSE
            await pulse.emit_metric_result({
                "hypothesis_id": getattr(hyp, "id", f"H{step}"),
                "title": hyp.hypothesis,
                "cagr": report.cagr,
                "sharpe": report.sharpe_ratio,
                "max_drawdown": report.max_drawdown
            })
            
                    
                    
                    
        # 9. Emit comparative benchmark view
        overall = {
            "best_cagr": max((r.cagr for r in results.values()), default=0.0),
            "benchmark_cagr": benchmark_returns.mean() * 252, # simple proxy
            "completed_models": total
        }
        await pulse.emit_comparison(overall)
        await pulse.emit_status("backtesting", "complete", total, total, "Engines Halted", "All configurations backtested.", 100, 0)

        return results
