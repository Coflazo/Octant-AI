export default function CitationCards({ citations }: { citations: any[] }) {
  return (
    <div className="grid grid-cols-2 gap-3">
      {citations.map((c, i) => {
        const borderCol = c.supports_hypothesis === true ? 'border-l-octGreen' : c.supports_hypothesis === false ? 'border-l-red-500' : 'border-l-gray-600';
        return (
          <div key={i} className={`bg-gray-900 border border-gray-800 border-l-4 p-3 rounded-r-md ${borderCol} flex flex-col justify-between`}>
            <div>
              <div className="text-xs font-bold text-gray-300 mb-1 line-clamp-2">{c.title}</div>
              <div className="text-[10px] text-gray-500 mb-1">{c.authors} ({c.year}) - {c.journal}</div>
            </div>
            <div className="flex justify-between items-center mt-2">
              <span className={`text-[10px] px-1.5 py-0.5 rounded ${c.relevance_score > 90 ? 'bg-octGreen/20 text-octGreen' : 'bg-gray-800 text-gray-400'}`}>
                {c.relevance_score}% Rel
              </span>
              <span className="text-[10px] text-gray-600">
                {c.supports_hypothesis === true ? 'SUPPORTS' : c.supports_hypothesis === false ? 'CONTRADICTS' : 'NEUTRAL'}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
