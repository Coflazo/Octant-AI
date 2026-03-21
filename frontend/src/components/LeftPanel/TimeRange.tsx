export default function TimeRange({ dateRange, setDateRange }: { dateRange: any, setDateRange: any }) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs text-gray-400 uppercase tracking-wider">Backtest Horizon</label>
      <div className="flex gap-2">
        <input type="date" value={dateRange.start} onChange={e => setDateRange({...dateRange, start: e.target.value})} className="w-1/2 bg-gray-900 border border-gray-700 text-white text-xs p-2 rounded focus:outline-none focus:border-octGreen" />
        <span className="text-gray-500 self-center">-</span>
        <input type="date" value={dateRange.end} onChange={e => setDateRange({...dateRange, end: e.target.value})} className="w-1/2 bg-gray-900 border border-gray-700 text-white text-xs p-2 rounded focus:outline-none focus:border-octGreen" />
      </div>
    </div>
  );
}
