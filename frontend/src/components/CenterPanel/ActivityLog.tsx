import { useEffect, useRef } from 'react';
import { PulseEvent } from '../../hooks/usePulseWebSocket';

export default function ActivityLog({ logs }: { logs: PulseEvent[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="h-48 bg-black/50 border border-gray-800 rounded-lg p-3 overflow-y-auto font-mono text-[10px] custom-scrollbar">
      <div className="text-gray-600 mb-2">-- System Log Start --</div>
      {logs.map((l, i) => (
        <div key={i} className="mb-1">
          <span className="text-gray-500">[{new Date(l.timestamp).toLocaleTimeString()}]</span>{' '}
          <span className="text-blue-400">[{l.payload_type}]</span>{' '}
          <span className="text-gray-300 truncate max-w-[80%] inline-block align-bottom">
            {l.message?.title || JSON.stringify(l.payload).slice(0, 120)}
          </span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
