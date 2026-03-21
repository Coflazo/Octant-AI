export default function SectorFilter({ sector, setSector }: { sector: string, setSector: (s: string) => void }) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs text-gray-400 uppercase tracking-wider">Sector Restriction</label>
      <select value={sector} onChange={e => setSector(e.target.value)} className="w-full bg-gray-900 border border-gray-700 text-white text-sm p-2 rounded focus:border-octGreen focus:outline-none">
        {['All', 'Technology', 'Healthcare', 'Financials', 'Consumer Discretionary', 'Energy', 'Industrials'].map(s => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>
    </div>
  );
}
