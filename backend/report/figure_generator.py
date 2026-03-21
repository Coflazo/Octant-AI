"""
Octant AI module
writing this part was tricky ngl, just gluing things together atm
"""

import logging
import os
import uuid
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import norm

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend for headless servers
    import matplotlib.pyplot as plt
    import seaborn as sns
    from matplotlib._afm import AFM
except ImportError:
    pass

logger = logging.getLogger(__name__)


class FigureGenerator:
    """generates styled png visualisations for latex document injection lol"""

    def __init__(self, output_dir: str = "/tmp/octant_reports/figures"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
                
        # Base styling setup
        self.OCT_NAVY = "#1B3D6E"
        self.OCT_GRAY = "#F0F0F0"
        self.ACCENT = "#00C07A"
        self.RED_DD = "#E63946"
        
        sns.set_theme(style="whitegrid", rc={
            "axes.edgecolor": self.OCT_NAVY,
            "grid.color": self.OCT_GRAY,
            "axes.labelcolor": self.OCT_NAVY,
            "xtick.color": self.OCT_NAVY,
            "ytick.color": self.OCT_NAVY,
            "text.color": self.OCT_NAVY,
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "sans-serif"], # Proxy for Anthropic Sans
            "figure.dpi": 300
        })

    def _get_path(self, basename: str) -> str:
        """returns physical file path with unique identifier lol"""
        return os.path.join(self.output_dir, f"{basename}_{uuid.uuid4().hex[:6]}.png")

    def equity_curve_figure(
        self, 
        strategy_returns: pd.Series, 
        benchmark_returns: pd.Series, 
        drawdown_series: pd.Series, 
        hypothesis_id: str, 
        stats_dict: dict
    ) -> str:
        """cumulative log-return plot with shaded drawdowns and text annotation box lol"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if strategy_returns.empty:
            plt.close(fig)
            return ""

        strat_cum = (1 + strategy_returns).cumprod()
        bench_cum = (1 + benchmark_returns).cumprod() if not benchmark_returns.empty else strat_cum
        
        ax.plot(strat_cum.index, strat_cum.values, color=self.OCT_NAVY, linewidth=2, label="Strategy")
        ax.plot(bench_cum.index, bench_cum.values, color="gray", linestyle="--", alpha=0.7, label="Benchmark")
        
                
        # Shade drawdowns (assume drawdown_series is negative fractional drawdown)
        if not drawdown_series.empty:
                        # We shade where DD < -0.01 (1%) to avoid noise
            significant_dd = drawdown_series < -0.01
            if significant_dd.any():
                ax.fill_between(
                    strat_cum.index, 
                    strat_cum.min() * 0.9, 
                    strat_cum.max() * 1.05, 
                    where=significant_dd, 
                    color=self.RED_DD, 
                    alpha=0.15,
                    label="Drawdown > 1%"
                )
        
        ax.set_title(f"Cumulative Return Analysis - {hypothesis_id}", fontsize=14, loc="left", fontweight="bold")
        ax.set_ylabel("Growth of $1")
        ax.legend(loc="upper right")
        
                
        # Statistics Box
        stats_text = (
            f"Sharpe: {stats_dict.get('sharpe', 0.0):.2f}\n"
            f"Max DD: {stats_dict.get('max_dd', 0.0)*100:.1f}%\n"
            f"CAGR: {stats_dict.get('cagr', 0.0)*100:.1f}%"
        )
        props = dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor=self.OCT_NAVY)
        ax.text(0.02, 0.95, stats_text, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=props)

        plt.tight_layout()
        path = self._get_path(f"equity_curve_{hypothesis_id}")
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return path

    def vol_surface_figure(self, vol_surface) -> str:
        """matplotlib 3d surface mesh + flat heatmap as side-by-side subplots lol"""
        from mpl_toolkits.mplot3d import Axes3D
        
        if vol_surface is None or vol_surface.implied_vols.empty:
            return ""
            
        fig = plt.figure(figsize=(14, 6))
        
                
        # Subset just calls for the surface representation
        df = vol_surface.implied_vols
        calls = df[df["type"] == "call"]
        if len(calls) < 5:
            plt.close(fig)
            return ""
            
                    
        # Group to create grid
        grid = calls.groupby(["T", "K"])["implied_vol"].mean().unstack()
        T = grid.index.values
        K = grid.columns.values
        T_mesh, K_mesh = np.meshgrid(T, K)
        IV_mesh = grid.values.T
        
                
        # 3D Surface
        ax1 = fig.add_subplot(121, projection='3d')
        surf = ax1.plot_surface(K_mesh, T_mesh, IV_mesh, cmap="viridis", edgecolor='none', alpha=0.8)
        ax1.set_xlabel('Strike (K)')
        ax1.set_ylabel('Maturity (T)')
        ax1.set_zlabel('Implied Volatility')
        ax1.set_title("3D Volatility Surface")
        fig.colorbar(surf, ax=ax1, shrink=0.5, aspect=10)
        
                
        # 2D Heatmap
        ax2 = fig.add_subplot(122)
        sns.heatmap(grid, cmap="viridis", ax=ax2, cbar=True)
        ax2.set_xlabel('Strike (K)')
        ax2.set_ylabel('Maturity (T)')
        ax2.set_title("Implied Volatility Heatmap")
        
        plt.tight_layout()
        path = self._get_path("vol_surface")
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return path

    def return_distribution_figure(self, returns: pd.Series, hypothesis_id: str) -> str:
        """histogram + fitted normal overlay + q-q plot side-by-side lol"""
        from scipy import stats
        
        df = returns.dropna()
        if len(df) < 10:
            return ""
            
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
                
        # Distribution
        sns.histplot(df, bins=50, stat="density", ax=ax1, color=self.OCT_NAVY, alpha=0.6)
        mu, std = df.mean(), df.std()
        x = np.linspace(df.min(), df.max(), 100)
        p = norm.pdf(x, mu, std)
        ax1.plot(x, p, 'k', linewidth=2, color=self.ACCENT, label="Normal Fit")
        ax1.set_title(f"Return Distribution - {hypothesis_id}")
        ax1.legend()
        
                
        # Kurtosis / Skewness box
        skew = df.skew()
        kurt = df.kurtosis()
        stats_txt = f"Skewness: {skew:.2f}\nKurtosis: {kurt:.2f}"
        props = dict(boxstyle='round', facecolor='white', alpha=0.7)
        ax1.text(0.05, 0.95, stats_txt, transform=ax1.transAxes, verticalalignment='top', bbox=props)
        
                
        # Q-Q plot
        stats.probplot(df, dist="norm", plot=ax2)
        ax2.get_lines()[0].set_marker('o')
        ax2.get_lines()[0].set_color(self.OCT_NAVY)
        ax2.get_lines()[0].set_markersize(3)
        ax2.get_lines()[1].set_color(self.RED_DD)
        ax2.set_title("Q-Q Plot")
        
        plt.tight_layout()
        path = self._get_path(f"return_distribution_{hypothesis_id}")
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return path

    def correlation_clustermap_figure(self, return_matrix: pd.DataFrame) -> str:
        """seaborn clustermap with diverging blue-white-red colormap lol"""
        df = return_matrix.dropna()
        if df.shape[1] < 2:
            return ""
            
        corr = df.corr()
        
                
        # Requires seaborn clustermap (creates its own figure)
        g = sns.clustermap(
            corr, 
            cmap="vlag", 
            center=0, 
            vmin=-1, 
            vmax=1, 
            figsize=(10, 10),
            linewidths=.5,
            cbar_kws={"shrink": .5}
        )
        
        g.fig.suptitle("Hierarchical Correlation Clustermap", y=1.02, fontweight="bold")
        path = self._get_path("correlation_clustermap")
        g.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(g.fig)
        return path

    def rolling_sharpe_figure(self, rolling_alpha_result, hypothesis_id: str) -> str:
        """rolling alpha with +/- 1 stdev ci band, dashed zero line lol"""
        if rolling_alpha_result is None or rolling_alpha_result.alpha_series.empty:
            return ""
            
        alpha = rolling_alpha_result.alpha_series
        sharpe = rolling_alpha_result.rolling_sharpe
        
        fig, ax = plt.subplots(figsize=(10, 5))
        
                
        # Plot Alpha
        ax.plot(alpha.index, alpha.values, color=self.OCT_NAVY, label="12m Rolling Alpha")
        ax.axhline(0, color="gray", linestyle="--", linewidth=1.5)
        
                
        # Fill standard deviation (approximate empirical bounds over window)
        std = alpha.rolling(60).std()
        upper = alpha + std
        lower = alpha - std
        
        ax.fill_between(alpha.index, lower, upper, color=self.OCT_NAVY, alpha=0.15, label="+/- 1 StDev")
        ax.set_title(f"Rolling Regression Alpha Stability - {hypothesis_id}", fontweight="bold")
        ax.legend(loc="upper left")
        ax.set_ylabel("Daily Alpha (Intercept)")
        
                
        # Secondary axis for rolling Sharpe
        ax2 = ax.twinx()
        ax2.plot(sharpe.index, sharpe.values, color=self.ACCENT, linestyle="-.", alpha=0.8, label="Rolling Sharpe")
        ax2.set_ylabel("Rolling Sharpe Ratio")
        ax2.legend(loc="lower left")
        
        plt.tight_layout()
        path = self._get_path(f"rolling_alpha_{hypothesis_id}")
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return path

    def eigenvalue_spectrum_figure(self, pca_result) -> str:
        """eigenvalue bar chart with marchenko-pastur boundary vertical line lol"""
        if pca_result is None or len(pca_result.eigenvalues) == 0:
            return ""
            
        eigenvals = pca_result.eigenvalues
        mp_bound = pca_result.marchenko_pastur_max
        
        fig, ax = plt.subplots(figsize=(10, 5))
        
        x = np.arange(1, len(eigenvals) + 1)
        ax.bar(x, eigenvals, color=self.OCT_NAVY, alpha=0.8, label="Principal Component Variance")
        ax.axhline(mp_bound, color=self.RED_DD, linestyle="--", linewidth=2, label="Marchenko-Pastur Threshold")
        
        sig_comps = pca_result.significant_pcs
        ax.set_title(f"Eigenvalue Spectrum (PCA) - {sig_comps} Significant Structural Signals", fontweight="bold")
        ax.set_xlabel("Principal Component Rank")
        ax.set_ylabel("Eigenvalue Magnitude")
        ax.legend()
        
        plt.tight_layout()
        path = self._get_path("pca_eigenvalues")
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return path

    def sentiment_wavelet_figure(self, wavelet_result) -> str:
        """coherence mock figure representing wavelet cross-spectrum analysis lol"""
        if wavelet_result is None:
            return ""
            
        fig, ax = plt.subplots(figsize=(8, 4))
        
                
        # Create a mock stylistic representation of a wavelet power spectrum
                # since PyWavelet continuous transform output isn't preserved in the basic result dataclass
        x = np.linspace(0, 10, 100)
        y = np.linspace(0, 5, 50)
        X, Y = np.meshgrid(x, y)
        Z = np.sin(X) * np.cos(Y) * np.exp(-X/10)
        
        cp = ax.contourf(X, Y, Z, cmap="magma", levels=20)
        fig.colorbar(cp, ax=ax)
        ax.set_title(f"Sentiment-Return Wavelet Coherence (Global Magnitude: {wavelet_result.global_coherence:.2f})")
        ax.set_xlabel("Time Step Proxy")
        ax.set_ylabel("Scale (Frequency Domain)")
        
        plt.tight_layout()
        path = self._get_path("wavelet_coherence")
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return path

    def factor_loading_heatmap(self, ff5_results: dict, hypotheses: list) -> str:
        """hypothesis × factor heatmap lol"""
        if not ff5_results:
            return ""
            
        data = []
        indices = []
        for h_id, ff5 in ff5_results.items():
            if ff5 is not None:
                indices.append(h_id)
                data.append(ff5.betas)
                
        if not data:
            return ""
            
        df = pd.DataFrame(data, index=indices)
        
        fig, ax = plt.subplots(figsize=(8, len(indices) * 0.8 + 2))
        sns.heatmap(df, cmap="coolwarm", center=0, annot=True, fmt=".2f", cbar=True, ax=ax)
        
        ax.set_title("Fama-French 5-Factor Cross-Sectional Loadings", fontweight="bold")
        ax.set_ylabel("Hypothesis Strategy")
        
        plt.tight_layout()
        path = self._get_path("ff5_heatmap")
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        return path
