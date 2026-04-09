import { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { usePulseWebSocket } from './hooks/usePulseWebSocket';
import type { PulseEvent } from './hooks/usePulseWebSocket';
import LeftPanel from './components/LeftPanel/index';
import CenterPanel from './components/CenterPanel/index';
import RightPanel from './components/RightPanel/index';
import './index.css';

export default function App() {
  const [sessionId] = useState(() => uuidv4());
  const { status: wsStatus, events } = usePulseWebSocket(sessionId);

  // Global State
  const [pipelineStatus, setPipelineStatus] = useState<string>("idle");
  const [thesis, setThesis] = useState("");
  const [exchanges, setExchanges] = useState<string[]>([]);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });
  const [sector, setSector] = useState("All");

  const [hypotheses, setHypotheses] = useState<Record<string, any>[]>([]);
  const [citations, setCitations] = useState<Record<string, any>[]>([]);
  const [tickers, setTickers] = useState<Record<string, any>[]>([]);
  const [metricsMatrix, setMetricsMatrix] = useState<Record<string, any>[]>([]);
  const [reportOutline, setReportOutline] = useState<Record<string, any>[]>([]);
  const [activityLog, setActivityLog] = useState<PulseEvent[]>([]);
  const [agentStatuses, setAgentStatuses] = useState<Record<string, PulseEvent>>({});
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);

  // Event Router — dispatches PULSE events to the correct state
  useEffect(() => {
    if (events.length === 0) return;
    const latest = events[events.length - 1];
    if (!latest || !latest.payload_type) return;

    setActivityLog(prev => {
      const next = [...prev, latest];
      return next.length > 200 ? next.slice(-200) : next;
    });

    switch (latest.payload_type) {
      case 'status':
        setAgentStatuses(prev => ({
          ...prev,
          [latest.agent]: latest,
        }));
        if (latest.agent === "orchestrator" && latest.status === "active") {
          setPipelineStatus("running");
        }
        if (latest.agent === "report" && latest.status === "complete") {
          setPipelineStatus("complete");
        }
        if (latest.agent === "orchestrator" && latest.status === "complete") {
          setPipelineStatus("complete");
        }
        if (latest.status === "error") {
          setPipelineStatus("error");
        }
        break;
      case 'hypothesis_card':
        setHypotheses(prev => [...prev, latest.payload]);
        break;
      case 'citation_card':
        setCitations(prev => [...prev, latest.payload]);
        break;
      case 'ticker_card':
        setTickers(prev => [...prev, latest.payload]);
        break;
      case 'metric_result':
        setMetricsMatrix(prev => [...prev, latest.payload]);
        break;
      case 'report_section':
        setReportOutline(prev => {
          const existing = prev.filter(p => p.section_name !== latest.payload.section_name);
          return [...existing, latest.payload];
        });
        break;
    }
  }, [events]);

  // Detect PDF URL from report completion status
  useEffect(() => {
    const reportStatus = agentStatuses["report"];
    if (reportStatus && reportStatus.status === "complete") {
      setPdfUrl(`/api/reports/octant_report_${sessionId}.pdf`);
    }
  }, [agentStatuses, sessionId]);

  const runPipeline = async () => {
    setPipelineStatus("running");
    setHypotheses([]); setCitations([]); setTickers([]); setMetricsMatrix([]);
    setReportOutline([]); setActivityLog([]); setPdfUrl(null);
    setAgentStatuses({});

    try {
      const res = await fetch('/api/pipeline/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          thesis,
          exchanges,
          time_range: [dateRange.start, dateRange.end],
          sector: sector === "All" ? null : sector,
        }),
      });
      if (!res.ok) {
        setPipelineStatus("error");
      }
    } catch (e) {
      console.error("Pipeline failed to start", e);
      setPipelineStatus("error");
    }
  };

  return (
    <div className="min-h-screen bg-oct-deep text-oct-light font-sans">
      <header className="border-b border-gray-800 p-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <img
            src="/assets/Octant_Logo.png"
            alt="Octant AI"
            className="h-8 object-contain"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
          <h1 className="text-xl font-bold tracking-tight">
            Octant AI
            <span className="text-gray-500 font-light text-sm ml-2">v0.2.0</span>
          </h1>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <div className={`w-2 h-2 rounded-full ${wsStatus === 'connected' ? 'bg-oct-green shadow-[0_0_8px_#00C07A]' : 'bg-red-500'}`} />
          WS: {wsStatus.toUpperCase()}
        </div>
      </header>

      <main className="grid grid-cols-[280px_1fr_320px] h-[calc(100vh-65px)] overflow-hidden">
        <LeftPanel
          thesis={thesis} setThesis={setThesis}
          exchanges={exchanges} setExchanges={setExchanges}
          dateRange={dateRange} setDateRange={setDateRange}
          sector={sector} setSector={setSector}
          runPipeline={runPipeline}
          pipelineStatus={pipelineStatus}
          sessionId={sessionId}
        />
        <CenterPanel
          agentStatuses={agentStatuses}
          hypotheses={hypotheses}
          citations={citations}
          tickers={tickers}
          metricsMatrix={metricsMatrix}
          activityLog={activityLog}
        />
        <RightPanel
          reportOutline={reportOutline}
          pdfUrl={pdfUrl}
          metricsMatrix={metricsMatrix}
          citations={citations}
          hypotheses={hypotheses}
        />
      </main>
    </div>
  );
}
