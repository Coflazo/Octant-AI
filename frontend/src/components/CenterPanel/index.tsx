import PipelineView from './PipelineView';
import HypothesisCards from './HypothesisCards';
import CitationCards from './CitationCards';
import TickerGrid from './TickerGrid';
import ResultsMatrix from './ResultsMatrix';
import ActivityLog from './ActivityLog';

export default function CenterPanel(props: any) {
  return (
    <div className="flex flex-col h-full overflow-y-auto p-6 gap-8 custom-scrollbar">
      <PipelineView statuses={props.agentStatuses} />
      
      {props.hypotheses.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-4 border-b border-gray-800 pb-2">Hypothesis Translation</h3>
          <HypothesisCards hypotheses={props.hypotheses} />
        </section>
      )}

      {props.tickers.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-4 border-b border-gray-800 pb-2">Universe Construction</h3>
          <TickerGrid tickers={props.tickers} />
        </section>
      )}

      {props.citations.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-4 border-b border-gray-800 pb-2">Prior Literature Validation</h3>
          <CitationCards citations={props.citations} />
        </section>
      )}

      {props.metricsMatrix.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-4 border-b border-gray-800 pb-2">Quantitative Cross-Section</h3>
          <ResultsMatrix metrics={props.metricsMatrix} />
        </section>
      )}

      <section className="mt-auto">
        <ActivityLog logs={props.activityLog} />
      </section>
    </div>
  );
}
