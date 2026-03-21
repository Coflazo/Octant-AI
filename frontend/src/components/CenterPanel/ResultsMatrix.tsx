export default function ResultsMatrix({ metrics }: { metrics: any[] }) {
  if (!metrics || metrics.length === 0) return null;

  return (
    <div className="overflow-x-auto border border-gray-800 rounded-md">
      <table className="w-full text-left bg-gray-900 border-collapse">
        <thead className="bg-[#0C0D11] border-b border-gray-800">
          <tr>
            <th className="p-2 text-[10px] uppercase font-bold text-gray-500 tracking-wider">Hypothesis</th>
            <th className="p-2 text-[10px] uppercase font-bold text-gray-500 tracking-wider text-right">CAGR</th>
            <th className="p-2 text-[10px] uppercase font-bold text-gray-500 tracking-wider text-right">Sharpe</th>
            <th className="p-2 text-[10px] uppercase font-bold text-gray-500 tracking-wider text-right">Max DD</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-800">
          {metrics.map((m, i) => {
            const hasEdge = m.sharpe > 1.0;
            return (
              <tr key={i} className={`hover:bg-gray-800/50 transition-colors ${hasEdge ? 'bg-octGreen/5' : ''}`}>
                <td className="p-2 text-xs text-gray-300 font-medium truncate max-w-[200px]" title={m.title}>{m.title}</td>
                <td className={`p-2 text-xs text-right font-mono ${m.cagr > 0 ? 'text-octGreen' : 'text-red-400'}`}>{(m.cagr * 100).toFixed(1)}%</td>
                <td className={`p-2 text-xs text-right font-mono ${hasEdge ? 'text-octGreen font-bold' : 'text-gray-400'}`}>{m.sharpe.toFixed(2)}</td>
                <td className="p-2 text-xs text-right font-mono text-red-400/80">{(m.max_drawdown * 100).toFixed(1)}%</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
