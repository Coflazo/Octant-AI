export default function ThesisInput({ thesis, setThesis }: { thesis: string, setThesis: (t: string) => void }) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-xs text-gray-400 uppercase tracking-wider">Trading Thesis</label>
      <textarea 
        className="w-full h-32 bg-gray-900 border border-gray-700 rounded-md p-3 text-sm focus:border-octGreen focus:outline-none focus:ring-1 focus:ring-octGreen/50 resize-none transition-all placeholder-gray-600 text-octLight"
        placeholder="e.g., Short-squeeze logic dictates that heavily shorted consumer discretionary stocks exhibit momentum divergence prior to earnings..."
        value={thesis}
        onChange={e => setThesis(e.target.value)}
      />
      <div className="text-right text-xs text-gray-600">{thesis.length} chars</div>
    </div>
  );
}
