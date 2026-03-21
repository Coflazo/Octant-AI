import { useCallback, useEffect, useRef, useState } from "react";

interface UseVoiceInputResult {
  isRecording: boolean;
  isConnecting: boolean;
  error: string | null;
  startRecording: (sessionId: string) => Promise<void>;
  stopRecording: () => void;
}

export function useVoiceInput(): UseVoiceInputResult {
  const [isRecording, setIsRecording] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  
  // Clean up all resources
  const cleanup = useCallback(() => {
    if (mediaRecorder.current && mediaRecorder.current.state !== "inactive") {
      mediaRecorder.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ text: "stop" }));
      socketRef.current.close();
    }
    mediaRecorder.current = null;
    streamRef.current = null;
    socketRef.current = null;
    setIsRecording(false);
    setIsConnecting(false);
  }, []);

  
  // Cleanup on unmount
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  const startRecording = async (sessionId: string) => {
    try {
      setError(null);
      setIsConnecting(true);

      
      // 1. Request microphone permissions
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      
      // 2. Open dedicated WebSocket for voice chunk streaming
            // (The main PULSE socket is for downstream events, this handles upstream binary)
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.host; // Handled by Vite proxy in dev
      const wsUrl = `${protocol}//${host}/api/voice/transcribe/${sessionId}`;
      
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      
      // Ensure binary payloads are treated as array buffers or blobs
      socket.binaryType = "blob";

      const connectionPromise = new Promise((resolve, reject) => {
        socket.onopen = () => resolve(true);
        socket.onerror = (e) => reject(new Error("WebSocket connection failed"));
      });

      await connectionPromise;

      
      // 3. Configure MediaRecorder for 250ms chunks
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorder.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0 && socket.readyState === WebSocket.OPEN) {
          socket.send(event.data);
        }
      };

      recorder.onstop = () => {
        if (socket.readyState === WebSocket.OPEN) {
                    // Explicit end-of-speech signal so backend knows to flush
          socket.send(JSON.stringify({ text: "stop" }));
          socket.close();
        }
      };

      
      // Start recording and pushing chunks every 250ms
      recorder.start(250);
      setIsRecording(true);
      setIsConnecting(false);

    } catch (err: any) {
      setError(err.message || "Failed to start recording");
      cleanup();
    }
  };

  const stopRecording = () => {
    cleanup();
  };

  return { isRecording, isConnecting, error, startRecording, stopRecording };
}
