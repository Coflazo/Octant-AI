const EXCHANGES = [
  { code: 'NYSE', label: 'NYSE' },
  { code: 'NASDAQ', label: 'NASDAQ' },
  { code: 'LSE', label: 'LSE' },
  { code: 'TSX', label: 'TSX' },
  { code: 'ASX', label: 'ASX' },
  { code: 'EURONEXT', label: 'Euronext' },
  { code: 'FRANKFURT', label: 'Frankfurt' },
  { code: 'TOKYO', label: 'Tokyo' },
  { code: 'HONG_KONG', label: 'HK' },
];

export default function ExchangeSelector({ exchanges, setExchanges }: { exchanges: string[], setExchanges: (e: string[]) => void }) {
  const toggle = (code: string) => {
    if (exchanges.includes(code)) setExchanges(exchanges.filter(x => x !== code));
    else setExchanges([...exchanges, code]);
  };

  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs text-gray-400 uppercase tracking-wider">Target Exchanges</label>
      <div className="grid grid-cols-3 gap-2">
        {EXCHANGES.map(ex => (
          <button
            key={ex.code}
            onClick={() => toggle(ex.code)}
            className={`text-xs p-1.5 rounded-sm border transition-colors ${exchanges.includes(ex.code) ? 'bg-oct-navy border-blue-500 text-white shadow-[0_0_8px_rgba(27,61,110,0.5)]' : 'bg-transparent border-gray-700 text-gray-500 hover:border-gray-500'}`}
          >
            {ex.label}
          </button>
        ))}
      </div>
    </div>
  );
}
