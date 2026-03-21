import AgentCard from './AgentCard';

const AGENTS = [
  { id: 'hypothesis', name: 'Agent 1: Hypothesis' },
  { id: 'literature', name: 'Agent 2: Literature' },
  { id: 'universe', name: 'Agent 3: Universe' },
  { id: 'backtesting', name: 'Agent 4: Engine' },
  { id: 'report', name: 'Agent 5: Report' }
];

export default function PipelineView({ statuses }: { statuses: any }) {
  if (Object.keys(statuses).length === 0) return (
     <div className="flex items-center justify-center p-12 border border-gray-800 rounded-lg bg-gray-900/20 text-gray-500 text-sm italic">
        Awaiting Deployment...
     </div>
  );

  return (
    <div className="grid grid-cols-5 gap-3 mb-4">
      {AGENTS.map((a, i) => (
        <AgentCard key={a.id} agent={a} status={statuses[a.id]} index={i} />
      ))}
    </div>
  );
}
