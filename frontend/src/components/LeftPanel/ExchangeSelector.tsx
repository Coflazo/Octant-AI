const EXCHANGES = ['NYSE', 'NASDAQ', 'LSE', 'TSX', 'ASX', 'Euronext', 'Frankfurt', 'Tokyo', 'HK'];

export default function ExchangeSelector({ exchanges, setExchanges }: { exchanges: string[], setExchanges: (e: string[]) => void }) {
  const toggle = (ex: string) => {
    if (exchanges.includes(ex)) setExchanges(exchanges.filter(x => x !== ex));
    else setExchanges([...exchanges, ex]);
  };

  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs text-gray-400 uppercase tracking-wider">Target Exchanges</label>
      <div className="grid grid-cols-3 gap-2">
        {EXCHANGES.map(ex => (
          <button
            key={ex}
            onClick={() => toggle(ex)}
            className={`text-xs p-1.5 rounded-sm border transition-colors ${exchanges.includes(ex) ? 'bg-octNavy border-blue-500 text-white shadow-[0_0_8px_rgba(27,61,110,0.5)]' : 'bg-transparent border-gray-700 text-gray-500 hover:border-gray-500'}`}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
