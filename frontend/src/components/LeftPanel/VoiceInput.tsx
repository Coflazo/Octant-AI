import { useVoiceInput } from '../../hooks/useVoiceInput';

export default function VoiceInput({ sessionId }: { sessionId: string }) {
  const { isRecording, isConnecting, error, startRecording, stopRecording } = useVoiceInput();

  const toggleRecord = async () => {
    if (!isRecording) {
      await startRecording(sessionId);
    } else {
      stopRecording();
    }
  };

  return (
    <div className="flex items-center gap-3 bg-gray-900/50 p-3 rounded-lg border border-gray-800">
      <button
        onClick={toggleRecord}
        disabled={isConnecting}
        className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${isRecording ? 'bg-red-500/20 text-red-500 animate-pulse border border-red-500' : 'bg-oct-navy hover:bg-oct-navy/80 text-white'}`}
      >
        <span className="text-xl leading-none">{isRecording ? '■' : '🎤'}</span>
      </button>
      <div className="text-sm text-gray-400">
        {isConnecting ? 'Connecting...' : isRecording ? 'Listening (Reson8 Active)...' : 'Dictate Hypothesis'}
      </div>
      {error && <div className="text-xs text-red-400">{error}</div>}
    </div>
  );
}
