export default function TickerGrid({ tickers }: { tickers: any[] }) {
  return (
    <div className="grid grid-cols-3 gap-3">
      {tickers.map((t, i) => (
        <div key={i} className="bg-gray-900 border border-gray-800 rounded-md p-3 flex flex-col relative overflow-hidden group hover:border-gray-500 transition-colors">
          <div className="flex justify-between items-center mb-2 z-10">
            <span className="font-bold text-white">{t.symbol}</span>
            <span className="text-[9px] bg-gray-800 px-1.5 py-0.5 rounded text-gray-400">{t.exchange}</span>
          </div>
          <div className="text-[10px] text-gray-500 mb-1 z-10">{t.sector}</div>
          <div className="text-[10px] text-gray-500 z-10">Cap: ${(t.market_cap / 1e9).toFixed(1)}B</div>
          
          {t.sparkline_url && (
            <img src={t.sparkline_url} className="absolute bottom-0 left-0 w-full h-1/2 object-cover opacity-30 group-hover:opacity-60 transition-opacity" alt={`${t.symbol} sparkline`} />
          )}
        </div>
      ))}
    </div>
  );
}
