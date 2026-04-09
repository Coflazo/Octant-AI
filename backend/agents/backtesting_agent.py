"""Agent 4: Backtesting Agent — dual backtesting engine."""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    import vectorbt as vbt
except ImportError:
    vbt = None

from backend.agents.hypothesis_engine import HypothesisObject
from backend.agents.universe_builder import UniverseBuildResult
from backend.pulse import PulseEmitter
from backend.math_engine.performance import PerformanceCalculator, PerformanceReport
from backend.math_engine.time_series import fit_garch_family, detect_vol_regimes
from backend.math_engine.stochastic import fit_ou_process

logger = logging.getLogger(__name__)


def construct_signal(
    hypothesis: HypothesisObject,
    price_matrix: Dict[str, pd.DataFrame],
    universe_df: pd.DataFrame,
    sentiment_signals: Dict,
    math_results: Dict,
) -> Tuple[pd.Series, pd.Series]:
    """Dynamically route hypothesis parameters into boolean entry/exit signals.

    Returns:
        (entries, exits) — boolean Series representing the unified portfolio signal.
    """
    cat = hypothesis.math_badge.lower()

    # Use first available ticker as representative
    target_ticker = "AAPL"
    if price_matrix and len(price_matrix) > 0:
        target_ticker = list(price_matrix.keys())[0]

    df = price_matrix.get(target_ticker, pd.DataFrame())
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=bool), pd.Series(dtype=bool)

    closes = df["Close"]
    returns = closes.pct_change().dropna()

    entries = pd.Series(False, index=closes.index)
    exits = pd.Series(False, index=closes.index)

    sentiment_z = 0.0
    if target_ticker in sentiment_signals:
        sentiment_z = sentiment_signals[target_ticker].z_score

    if "time_series" in cat or "arima" in cat:
        ma_short = closes.rolling(10).mean()
        ma_long = closes.rolling(50).mean()
        entries = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
        exits = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))

    elif "mean_reversion" in cat or "cointegration" in cat:
        roll_mean = closes.rolling(20).mean()
        roll_std = closes.rolling(20).std()
        z = (closes - roll_mean) / roll_std
        entries = z < -2.0
        exits = z > 0.0

    elif "factor_model" in cat:
        weekly_ret = closes.pct_change(5)
        entries = (weekly_ret > 0.01) & (sentiment_z > 0.5)
        exits = weekly_ret < -0.01

    elif "regime_detection" in cat:
        garch_res = fit_garch_family(returns)
        if garch_res:
            hmm_res = detect_vol_regimes(garch_res.conditional_volatility)
            if hmm_res:
                prob_high = hmm_res.regime_probs
                entries = prob_high < 0.2
                exits = prob_high > 0.8
                entries = entries.reindex(closes.index, fill_value=False)
                exits = exits.reindex(closes.index, fill_value=False)

    elif "volatility" in cat or "options" in cat or "garch" in cat:
        roll_std = closes.rolling(20).std()
        entries = roll_std > roll_std.rolling(50).mean() * 1.5
        exits = roll_std < roll_std.rolling(50).mean()

    else:
        entries = closes > closes.rolling(20).mean()
        exits = closes < closes.rolling(20).mean()

    # Block entries if Reddit sentiment is highly bearish
    if sentiment_z < -2.0:
        entries = entries & False

    return entries.fillna(False), exits.fillna(False)


def run_vbt_backtest(
    entries: pd.Series, exits: pd.Series, price_data: pd.Series, long_only: bool
) -> Dict:
    """Run a vectorized backtest using VectorBT."""
    if vbt is None or entries.sum() == 0:
        return {"cagr": 0.0, "sharpe": 0.0, "max_dd": 0.0, "win_rate": 0.0}

    try:
        portfolio = vbt.Portfolio.from_signals(
            price_data, entries, exits,
            fees=0.0002, slippage=0.0001, freq="d",
        )
        stats = portfolio.stats()
        return {
            "cagr": stats.get("Total Return [%]", 0.0) / 100.0,
            "sharpe": stats.get("Sharpe Ratio", 0.0),
            "max_dd": stats.get("Max Drawdown [%]", 0.0) / 100.0,
            "win_rate": stats.get("Win Rate [%]", 0.0) / 100.0,
            "portfolio": portfolio,
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
    regime_series: Optional[pd.Series] = None,
) -> Tuple[pd.DataFrame, Dict]:
    """Iterative Python engine generating explainable, row-by-row trade logs."""
    trade_log = []
    in_position = False
    entry_price = 0.0
    entry_date = None

    df = pd.DataFrame({
        "Close": price_data,
        "Enter": entries,
        "Exit": exits,
        "Signal": signal_values,
    }).dropna()

    for date, row in df.iterrows():
        if row["Enter"] and not in_position:
            in_position = True
            entry_price = row["Close"]
            entry_date = date
        elif row["Exit"] and in_position:
            in_position = False
            exit_price = row["Close"]
            ret = (exit_price - entry_price) / entry_price - 0.0002
            trade_log.append({
                "entry_date": entry_date,
                "exit_date": date,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "return": ret,
                "signal_at_entry": row.get("Signal", 0.0),
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
    """Agent 4: Dual backtesting engine (VectorBT + explainable)."""

    def __init__(self):
        self.perf_calc = PerformanceCalculator()

    async def run(
        self,
        universe_result: UniverseBuildResult,
        hypotheses: List[HypothesisObject],
        citations_db: Dict,
        pulse: PulseEmitter,
    ) -> Dict[str, PerformanceReport]:
        """Run backtests for all hypotheses."""
        total = len(hypotheses)
        results: Dict[str, PerformanceReport] = {}

        await pulse.emit_status(
            "backtesting", "active", 0, total,
            "Initialising Engines", "VectorBT + Explainable Loop",
            0, total * 30,
        )

        # Determine benchmark ticker
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
            await pulse.emit_status(
                "backtesting", "active", step, total,
                f"Testing Sub-Hypothesis {step}", hyp.statement[:60],
                int((step / total) * 100), (total - step) * 30,
            )

            math_results = {}

            entries, exits = construct_signal(
                hypothesis=hyp,
                price_matrix=universe_result.price_matrix,
                universe_df=universe_result.universe_df,
                sentiment_signals=universe_result.sentiment_signals,
                math_results=math_results,
            )

            vbt_stats = run_vbt_backtest(entries, exits, price_df["Close"], long_only=True)

            portfolio = vbt_stats.get("portfolio")
            if portfolio is not None:
                strat_returns = portfolio.returns()
            else:
                strat_returns = pd.Series(0.0, index=benchmark_returns.index)

            sig_vals = pd.Series(0.0, index=price_df.index)
            log_df, custom_stats = run_custom_backtest(
                entries, exits, price_df["Close"], sig_vals
            )

            # Prior literature Sharpe estimate
            prior_sr = 0.5
            if hyp.id in citations_db and len(citations_db[hyp.id]) > 3:
                prior_sr = 0.8

            garch_vol = pd.Series(0.15, index=strat_returns.index)
            regime = pd.Series(1)

            report = self.perf_calc.compute_all(
                strategy_returns=strat_returns,
                benchmark_returns=benchmark_returns,
                rf_rate=0.02,
                ff5_factors=universe_result.ff5_factors,
                garch_cond_vol=garch_vol,
                regime_series=regime,
                sentiment_factor=None,
                hypothesis=hyp,
                prior_literature_sharpe=prior_sr,
            )

            # Backfill from VectorBT if custom engine returned zeroes
            if report.cagr == 0 and vbt_stats.get("cagr") != 0:
                report.cagr = vbt_stats["cagr"]
                report.sharpe_ratio = vbt_stats["sharpe"]
                report.max_drawdown = vbt_stats["max_dd"]

            results[hyp.id] = report

            # Emit individual metric result
            await pulse.emit_metric_result(
                hypothesis_id=hyp.id,
                metrics_obj={
                    "title": hyp.statement,
                    "cagr": report.cagr,
                    "sharpe_ratio": report.sharpe_ratio,
                    "max_drawdown": report.max_drawdown,
                },
            )

        await pulse.emit_status(
            "backtesting", "complete", total, total,
            "Engines Complete", "All configurations backtested.",
            100, 0,
        )

        return results
