export default function AgentCard({ agent, status, index }: { agent: any, status: any, index: number }) {
  const isActive = status?.status === 'active';
  const isComplete = status?.status === 'complete';
  const isError = status?.status === 'error';
  
  const pct = status && status.total > 0 ? Math.round((status.step / status.total) * 100) : 0;

  return (
    <div className={`p-3 border rounded-md transition-all duration-500 delay-[${index * 100}ms] ${isActive ? 'bg-octNavy/20 border-blue-500 shadow-[0_0_10px_rgba(27,61,110,0.5)]' : isComplete ? 'bg-gray-900/50 border-octGreen/50' : 'bg-gray-900 border-gray-800 opacity-60'}`}>
      <div className="flex justify-between items-center mb-2">
        <span className="text-[10px] uppercase font-bold text-gray-400">{agent.name}</span>
        {isActive && <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />}
        {isComplete && <div className="text-octGreen text-xs">✓</div>}
        {isError && <div className="text-red-500 text-xs">✕</div>}
      </div>
      <div className="text-xs text-white truncate">{status?.headline || 'Pending'}</div>
      <div className="text-[10px] text-gray-500 truncate mb-2">{status?.detail || '-'}</div>
      
      <div className="w-full bg-gray-800 h-1 rounded-full overflow-hidden">
        <div className={`h-full transition-all duration-300 ${isComplete ? 'bg-octGreen' : isError ? 'bg-red-500' : 'bg-blue-500'}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
