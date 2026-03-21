import ReportOutline from './ReportOutline';
import DownloadPDF from './DownloadPDF';
import TopMetrics from './TopMetrics';

export default function RightPanel(props: any) {
  return (
    <div className="border-l border-gray-800 p-4 flex flex-col gap-6 overflow-y-auto bg-[#0C0D11] custom-scrollbar">
      <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-2">Report Synthesizer</h2>
      <TopMetrics metrics={props.metricsMatrix} citations={props.citations} hypotheses={props.hypotheses} />
      <ReportOutline sections={props.reportOutline} />
      <div className="flex-grow" />
      <DownloadPDF url={props.pdfUrl} />
    </div>
  );
}
