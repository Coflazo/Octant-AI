import { useState, useRef } from 'react';

export default function VoiceInput({ sendMessage }: { sendMessage: (m: ArrayBuffer) => void }) {
  const [recording, setRecording] = useState(false);
  const mediaRecorder = useRef<MediaRecorder | null>(null);

  const toggleRecord = async () => {
    if (!recording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' });
        mr.ondataavailable = (e) => {
          if (e.data.size > 0 && e.data.arrayBuffer) {
            e.data.arrayBuffer().then(buf => sendMessage(buf));
          }
        };
        mr.start(500); // 500ms chunks
        mediaRecorder.current = mr;
        setRecording(true);
      } catch (err) {
        console.error("Mic access denied or error:", err);
      }
    } else {
      if (mediaRecorder.current) {
        mediaRecorder.current.stop();
        mediaRecorder.current.stream.getTracks().forEach(t => t.stop());
      }
      setRecording(false);
    }
  };

  return (
    <div className="flex items-center gap-3 bg-gray-900/50 p-3 rounded-lg border border-gray-800">
      <button 
        onClick={toggleRecord}
        className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${recording ? 'bg-red-500/20 text-red-500 animate-pulse border border-red-500' : 'bg-octNavy hover:bg-octNavy/80 text-white'}`}
      >
        <span className="text-xl leading-none">{recording ? '■' : '🎤'}</span>
      </button>
      <div className="text-sm text-gray-400">
        {recording ? 'Listening (Reson8 Active)...' : 'Dictate Hypothesis'}
      </div>
    </div>
  );
}
