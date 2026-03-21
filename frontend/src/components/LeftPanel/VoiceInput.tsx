import React, from "react";
import { useVoiceInput } from "../../hooks/useVoiceInput";
import { formatETA } from "../../utils/formatters";

interface VoiceInputProps {
  sessionId: string;
  streamingTranscript: string;
  isTranscriptionComplete: boolean;
  onTranscriptLocked: (text: string) => void;
}

/**
 * VoiceInput Component.
 *
 * Captures microphone audio, streams 250ms chunks to Reson8 via the backend,
 * and displays the streaming partial transcripts.
 */
export const VoiceInput: React.FC<VoiceInputProps> = ({
  sessionId,
  streamingTranscript,
  isTranscriptionComplete,
  onTranscriptLocked,
}) => {
  const {
    isRecording,
    isConnecting,
    error,
    startRecording,
    stopRecording,
  } = useVoiceInput();

  // If the backend silence detector finalises the transcript,
  // we automatically stop the mic and pass the text up.
  React.useEffect(() => {
    if (isTranscriptionComplete && isRecording) {
      stopRecording();
      onTranscriptLocked(streamingTranscript);
    }
  }, [isTranscriptionComplete, isRecording, streamingTranscript, onTranscriptLocked, stopRecording]);

  const handleToggle = () => {
    if (isRecording || isConnecting) {
      stopRecording();
    } else {
      startRecording(sessionId);
    }
  };

  return (
    <div className="bg-oct-surface border border-oct-border rounded p-4 mb-4 flex flex-col items-center justify-center">
      <div className="flex flex-col items-center">
        {/* Animated Microphone Button */}
        <button
          onClick={handleToggle}
          disabled={isConnecting}
          className={`relative flex items-center justify-center w-16 h-16 rounded-full transition-colors ${
            isRecording
              ? "bg-oct-green animate-pulse-green"
              : isConnecting
              ? "bg-oct-border"
              : "bg-oct-border hover:bg-opacity-80 border-2 border-transparent hover:border-oct-green"
          }`}
          aria-label={isRecording ? "Stop dictation" : "Start dictation"}
        >
          {isRecording ? (
            /* Stop Icon */
            <div className="w-5 h-5 bg-oct-deep rounded-sm"></div>
          ) : (
            /* Mic Icon (SVG) */
            <svg
              className="w-6 h-6 text-oct-text"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          )}
        </button>

        <span className="mt-2 text-sm text-oct-text-dim">
          {isRecording ? "Listening..." : isConnecting ? "Connecting..." : "Tap to speak thesis"}
        </span>
      </div>

      {error && (
        <div className="mt-3 text-sm text-oct-red text-center">
          {error}
        </div>
      )}

      {/* Real-time Streaming Transcript Display */}
      {streamingTranscript && !isTranscriptionComplete && (
        <div className="mt-4 w-full p-3 bg-oct-deep-light border border-oct-border rounded shadow-inner text-sm text-oct-text italic min-h-[60px] max-h-[120px] overflow-y-auto">
          "{streamingTranscript}"
          <span className="inline-block w-1.5 h-4 ml-1 bg-oct-green animate-pulse align-middle"></span>
        </div>
      )}
    </div>
  );
};
