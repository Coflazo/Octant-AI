export default function TopMetrics({ metrics, citations, hypotheses }: { metrics: Record<string, any>[], citations: Record<string, any>[], hypotheses: Record<string, any>[] }) {
  const bestSharpe = metrics.length > 0
    ? Math.max(...metrics.map(m => m.sharpe_ratio ?? 0)).toFixed(2)
    : '-';
  const worstDd = metrics.length > 0
    ? (Math.min(...metrics.map(m => m.max_drawdown ?? 0)) * 100).toFixed(1) + '%'
    : '-';

  return (
    <div className="grid grid-cols-2 gap-2">
      <div className="bg-gray-900 border border-gray-800 p-3 rounded-md shadow-sm">
        <div className="text-[10px] text-gray-500 uppercase">Top Config SR</div>
        <div className="text-lg font-bold text-oct-green font-mono">{bestSharpe}</div>
      </div>
      <div className="bg-gray-900 border border-gray-800 p-3 rounded-md shadow-sm">
        <div className="text-[10px] text-gray-500 uppercase">Worst Drawdown</div>
        <div className="text-lg font-bold text-red-500 font-mono">{worstDd}</div>
      </div>
      <div className="bg-gray-900 border border-gray-800 p-3 rounded-md shadow-sm">
        <div className="text-[10px] text-gray-500 uppercase">Sub-Hypotheses</div>
        <div className="text-lg font-bold text-white font-mono">{hypotheses.length || '-'}</div>
      </div>
      <div className="bg-gray-900 border border-gray-800 p-3 rounded-md shadow-sm">
        <div className="text-[10px] text-gray-500 uppercase">Papers Cited</div>
        <div className="text-lg font-bold text-blue-400 font-mono">{citations.length || '-'}</div>
      </div>
    </div>
  );
}
