/**
 * Octant AI — PULSE WebSocket Protocol Type Definitions.
 *
 * Every real-time event flowing between the FastAPI backend and the React
 * frontend conforms to the PulseEvent interface. Payload types are
 * discriminated by the payload_type field, enabling exhaustive TypeScript
 * pattern matching in the event router.
 */




// ── Agent identifiers (one per pipeline stage) ──────────────────────────

export type AgentName =
  | "hypothesis_engine"
  | "literature"
  | "universe"
  | "backtest"
  | "architect";




// ── Status lifecycle states ─────────────────────────────────────────────

export type PulseStatus = "pending" | "active" | "complete" | "error";




// ── Payload type discriminator ──────────────────────────────────────────

export type PayloadType =
  | "status"
  | "hypothesis_card"
  | "citation_card"
  | "ticker_card"
  | "metric_result"
  | "report_section"
  | "transcription"
  | "transcription_complete"
  | "error";




// ── Progress tracker ────────────────────────────────────────────────────

export interface PulseProgress {
  current_step: number;
  total_steps: number;
  percent_complete: number;
  estimated_remaining_sec: number;
}




// ── Display message ─────────────────────────────────────────────────────

export interface PulseMessage {
  title: string;
  subtitle: string;
}




// ── Hypothesis Card Payload ─────────────────────────────────────────────

export type MathMethodCategory =
  | "time_series"
  | "cross_sectional"
  | "volatility_surface"
  | "options_pricing"
  | "regime_detection"
  | "mean_reversion"
  | "factor_model";

export interface HypothesisCard {
  id: string;
  statement: string;
  null_hypothesis: string;
  math_badge: MathMethodCategory;
  direction: "+1" | "-1";
  key_variables: string[];
  relevant_math_models: string[];
  geographic_scope: string[];
  asset_class: string;
}




// ── Citation Card Payload ───────────────────────────────────────────────

export interface CitationCard {
  title: string;
  authors: string;
  year: number;
  journal: string;
  relevance: number;
  supports: boolean | null;
  abstract_summary: string;
  url: string;
  doi: string | null;
  key_finding: string;
  signal_tested: string;
  market_studied: string;
  time_period: string;
  performance_metric: string;
  statistical_methodology: string;
  effect_size: number | null;
  novelty_score: number;
}




// ── Ticker Card Payload ─────────────────────────────────────────────────

export interface TickerCard {
  symbol: string;
  name: string;
  exchange: string;
  sector: string;
  sparkline_url: string;
  mktcap: number;
  short_interest: number;
  days_to_cover: number;
  pb_ratio: number | null;
  avg_volume: number;
  sentiment_z_score: number | null;
}




// ── Metric Result Payload ───────────────────────────────────────────────

export interface MetricResult {
  hypothesis_id: string;

  
  
  
  // Return metrics
  total_return: number;
  cagr: number;
  annualised_excess_return: number;

  
  
  
  // Risk metrics
  annualised_vol: number;
  max_drawdown: number;
  max_drawdown_duration_days: number;
  calmar_ratio: number;

  
  
  
  // Risk-adjusted
  sharpe_ratio: number;
  sortino_ratio: number;
  information_ratio: number;
  omega_ratio: number;

  
  
  
  // Statistical
  t_statistic: number;
  bootstrap_p_value: number;
  alpha_t_statistic: number;
  factor_alpha_p_value: number;
  bonferroni_pass: boolean;
  bh_pass: boolean;
  bayes_adjusted_sharpe: number;

  
  
  
  // Transaction cost sensitivity
  breakeven_cost_bps: number;
  return_at_2bps: number;
  return_at_10bps: number;

  
  
  
  // Volatility
  garch_persistence: number;
  vol_regime_fraction_high: number;

  
  
  
  // Sentiment
  sentiment_factor_loading: number | null;
  sentiment_factor_t_stat: number | null;
}




// ── Report Section Payload ──────────────────────────────────────────────

export interface ReportSection {
  section_name: string;
  excerpt: string;
  is_complete: boolean;
}




// ── Transcription Payload ───────────────────────────────────────────────

export interface TranscriptionPayload {
  text: string;
  is_final: boolean;
}




// ── Error Payload ───────────────────────────────────────────────────────

export interface ErrorPayload {
  agent: AgentName;
  error_message: string;
  traceback: string;
  recovery_action: string | null;
}




// ── Union of all payload shapes ─────────────────────────────────────────

export type PulsePayload =
  | HypothesisCard
  | CitationCard
  | TickerCard
  | MetricResult
  | ReportSection
  | TranscriptionPayload
  | ErrorPayload
  | Record<string, unknown>; // fallback for "status" events with freeform data




// ── Top-level PULSE event envelope ──────────────────────────────────────

export interface PulseEvent {
  type: "PULSE";
  agent: AgentName;
  status: PulseStatus;
  progress: PulseProgress;
  payload_type: PayloadType;
  payload: PulsePayload;
  message: PulseMessage;
  timestamp: string;
}




// ── Exchange supported by Universe Builder ──────────────────────────────

export type SupportedExchange =
  | "NYSE"
  | "NASDAQ"
  | "LSE"
  | "TSX"
  | "ASX"
  | "EURONEXT_PA"
  | "EURONEXT_AS"
  | "FRANKFURT"
  | "TOKYO"
  | "HONG_KONG";

export interface ExchangeInfo {
  code: SupportedExchange;
  label: string;
  suffix: string;
  flag: string;
}

export const EXCHANGES: ExchangeInfo[] = [
  { code: "NYSE",        label: "NYSE",             suffix: "",   flag: "🇺🇸" },
  { code: "NASDAQ",      label: "NASDAQ",           suffix: "",   flag: "🇺🇸" },
  { code: "LSE",         label: "London",           suffix: ".L", flag: "🇬🇧" },
  { code: "TSX",         label: "Toronto",          suffix: ".TO",flag: "🇨🇦" },
  { code: "ASX",         label: "Australian",       suffix: ".AX",flag: "🇦🇺" },
  { code: "EURONEXT_PA", label: "Euronext Paris",   suffix: ".PA",flag: "🇫🇷" },
  { code: "EURONEXT_AS", label: "Euronext Amsterdam",suffix: ".AS",flag: "🇳🇱" },
  { code: "FRANKFURT",   label: "Frankfurt",        suffix: ".DE",flag: "🇩🇪" },
  { code: "TOKYO",       label: "Tokyo",            suffix: ".T", flag: "🇯🇵" },
  { code: "HONG_KONG",   label: "Hong Kong",        suffix: ".HK",flag: "🇭🇰" },
];




// ── Pipeline request shape (mirrors backend PipelineRequest) ────────────

export interface PipelineRequest {
  thesis_str: string;
  exchanges: SupportedExchange[];
  time_range: {
    start_date: string;
    end_date: string;
  };
  sector_filter: string | null;
  session_id: string;
}




// ── Pipeline status (mirrors backend SessionState) ──────────────────────

export type PipelineStatus =
  | "idle"
  | "running"
  | "completed"
  | "stopped"
  | "error";




// ── Significance labels ─────────────────────────────────────────────────

export type SignificanceLabel =
  | "strongly significant"
  | "significant"
  | "not significant";




// ── Top-level application state ─────────────────────────────────────────

export interface OctantState {
  session_id: string;
  pipeline_status: PipelineStatus;
  hypotheses: HypothesisCard[];
  citations: CitationCard[];
  tickers: TickerCard[];
  metrics: MetricResult[];
  report_sections: ReportSection[];
  pdf_url: string | null;
  activity_log: string[];
  error: ErrorPayload | null;
  agent_statuses: Record<AgentName, PulseStatus>;
  agent_progress: Record<AgentName, PulseProgress | null>;
}
