export default function HypothesisCards({ hypotheses }: { hypotheses: any[] }) {
  return (
    <div className="flex flex-col gap-3">
      {hypotheses.map((h, i) => (
        <div key={i} className="bg-gray-900/60 border border-gray-800 p-4 rounded-lg flex items-start gap-4 transition-all duration-500" style={{ animationDelay: `${i*100}ms` }}>
           <div className="min-w-[40px] h-[40px] rounded bg-octNavy text-blue-300 flex items-center justify-center font-bold text-sm">
             H{i+1}
           </div>
           <div className="flex-1">
             <div className="text-sm text-gray-200 font-medium mb-1">{h.hypothesis}</div>
             <div className="text-xs text-gray-500 italic mb-2">Null: {h.null_hypothesis}</div>
             <div className="flex gap-2">
               <span className="text-[10px] bg-blue-900/40 text-blue-400 border border-blue-800 px-2 py-0.5 rounded-full uppercase">{h.math_method_category}</span>
               <span className="text-[10px] bg-gray-800 text-gray-400 border border-gray-700 px-2 py-0.5 rounded-full uppercase">{h.direction}</span>
             </div>
           </div>
        </div>
      ))}
    </div>
  );
}
