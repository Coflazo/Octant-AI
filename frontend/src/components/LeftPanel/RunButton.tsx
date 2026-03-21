export default function RunButton({ runPipeline, status }: { runPipeline: () => void, status: string }) {
  const isRunning = status === 'running';
  return (
    <button
      onClick={runPipeline}
      disabled={isRunning}
      className={`w-full py-4 text-sm font-bold tracking-widest uppercase rounded-md transition-all ${isRunning ? 'bg-gray-800 text-gray-600 cursor-not-allowed border border-gray-700' : 'bg-octGreen text-octDeep hover:bg-[#00e08f] shadow-[0_0_15px_rgba(0,192,122,0.4)] hover:shadow-[0_0_25px_rgba(0,192,122,0.6)]'}`}
    >
      {isRunning ? 'Compiling Protocol...' : 'Deploy Analytics'}
    </button>
  );
}
