import VoiceInput from './VoiceInput';
import ThesisInput from './ThesisInput';
import ExchangeSelector from './ExchangeSelector';
import TimeRange from './TimeRange';
import SectorFilter from './SectorFilter';
import RunButton from './RunButton';

interface Props {
  thesis: string; setThesis: (t: string) => void;
  exchanges: string[]; setExchanges: (e: string[]) => void;
  dateRange: {start: string, end: string}; setDateRange: (d: {start: string, end: string}) => void;
  sector: string; setSector: (s: string) => void;
  runPipeline: () => void;
  pipelineStatus: string;
  sendMessage: (m: any) => void;
}

export default function LeftPanel(props: Props) {
  return (
    <div className="border-r border-gray-800 p-4 flex flex-col gap-6 overflow-y-auto bg-[#0C0D11]">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-2">Research Configuration</h2>
      <VoiceInput sendMessage={props.sendMessage} />
      <ThesisInput thesis={props.thesis} setThesis={props.setThesis} />
      <ExchangeSelector exchanges={props.exchanges} setExchanges={props.setExchanges} />
      <TimeRange dateRange={props.dateRange} setDateRange={props.setDateRange} />
      <SectorFilter sector={props.sector} setSector={props.setSector} />
      <div className="flex-grow" />
      <RunButton runPipeline={props.runPipeline} status={props.pipelineStatus} />
    </div>
  );
}
