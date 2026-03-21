import { useState, useEffect } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { usePulseWebSocket } from './hooks/usePulseWebSocket';
import LeftPanel from './components/LeftPanel';
import CenterPanel from './components/CenterPanel';
import RightPanel from './components/RightPanel';
import './index.css';

export default function App() {
    const [sessionId] = useState(() => uuidv4());
    const { status: wsStatus, events, sendMessage } = usePulseWebSocket(sessionId);
    
    // Global State
    const [pipelineStatus, setPipelineStatus] = useState<string>("idle");
    const [thesis, setThesis] = useState("");
    const [exchanges, setExchanges] = useState<string[]>([]);
    const [dateRange, setDateRange] = useState({ start: '', end: '' });
    const [sector, setSector] = useState("All");
    
    const [hypotheses, setHypotheses] = useState<any[]>([]);
    const [citations, setCitations] = useState<any[]>([]);
    const [tickers, setTickers] = useState<any[]>([]);
    const [metricsMatrix, setMetricsMatrix] = useState<any[]>([]);
    const [reportOutline, setReportOutline] = useState<any[]>([]);
    const [activityLog, setActivityLog] = useState<any[]>([]);
    const [agentStatuses, setAgentStatuses] = useState<any>({});
    const [pdfUrl, setPdfUrl] = useState<string | null>(null);

    // Event Router
    useEffect(() => {
        if (events.length === 0) return;
        const latest = events[events.length - 1];
        if (!latest || !latest.type) return;

        setActivityLog(prev => [...prev, latest]);

        switch (latest.type) {
            case 'status':
                setAgentStatuses((prev: any) => ({
                    ...prev,
                    [latest.payload.agent_id]: latest.payload
                }));
                if (latest.payload.agent_id === "report" && latest.payload.status === "complete") {
                    setPipelineStatus("complete");
                    setPdfUrl(`http://localhost:8000/download/octant_report_${sessionId}.pdf`); // mock 
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
                    const existing = prev.filter(p => p.section !== latest.payload.section);
                    return [...existing, latest.payload];
                });
                break;
            case 'voice_transcript':
                if (latest.payload.is_final) {
                    setThesis(prev => prev + " " + latest.payload.text);
                }
                break;
        }
    }, [events, sessionId]);

    const runPipeline = async () => {
        setPipelineStatus("running");
        setHypotheses([]); setCitations([]); setTickers([]); setMetricsMatrix([]);
        setReportOutline([]); setActivityLog([]); setPdfUrl(null);
        setAgentStatuses({});
        
        try {
            await fetch(`http://localhost:8000/api/research/run`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    thesis: thesis,
                    exchanges: exchanges,
                    time_range: [dateRange.start, dateRange.end],
                    sector: sector === "All" ? null : sector
                })
            });
        } catch(e) {
            console.error("Pipeline failed to start", e);
            setPipelineStatus("error");
        }
    };

    return (
        <div className="min-h-screen bg-octDeep text-octLight font-sans">
            <header className="border-b border-gray-800 p-4 flex justify-between items-center">
                <div className="flex items-center gap-3">
                    <img src="/assets/Octant_Logo.png" alt="Octant AI" className="h-8 object-contain" onError={(e) => { e.currentTarget.style.display='none' }} />
                    <h1 className="text-xl font-bold tracking-tight">Octant AI <span className="text-gray-500 font-light text-sm ml-2">v0.1.0-alpha</span></h1>
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-400">
                    <div className={`w-2 h-2 rounded-full ${wsStatus === 'connected' ? 'bg-octGreen shadow-[0_0_8px_#00C07A]' : 'bg-red-500'}`} />
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
                    sendMessage={sendMessage}
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
