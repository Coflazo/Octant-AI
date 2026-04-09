import { useState, useEffect, useCallback, useRef } from 'react';

export interface PulseEvent {
  type: string;
  agent: string;
  status: string;
  progress: {
    current_step: number;
    total_steps: number;
    percent_complete: number;
    estimated_remaining_sec: number;
  };
  payload_type: string;
  payload: Record<string, any>;
  message: {
    title: string;
    subtitle: string;
  };
  timestamp: string;
}

export function usePulseWebSocket(sessionId: string) {
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected" | "error">("connecting");
  const [events, setEvents] = useState<PulseEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const retryCount = useRef(0);
  const maxRetries = 5;

  const connect = useCallback(() => {
    if (!sessionId) return;

    setStatus("connecting");
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const ws = new WebSocket(`${protocol}//${host}/ws/${sessionId}`);

    ws.onopen = () => {
      setStatus("connected");
      retryCount.current = 0;
    };

    ws.onmessage = (msg) => {
      try {
        const data = JSON.parse(msg.data);
        setEvents(prev => {
          const next = [...prev, data];
          return next.length > 500 ? next.slice(-500) : next;
        });
      } catch {
        // Non-JSON message, ignore
      }
    };

    ws.onclose = () => {
      setStatus("disconnected");
      if (retryCount.current < maxRetries) {
        const delay = Math.pow(2, retryCount.current) * 1000;
        retryCount.current += 1;
        setTimeout(connect, delay);
      } else {
        setStatus("error");
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [sessionId]);

  useEffect(() => {
    connect();
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  const sendMessage = useCallback((data: string | ArrayBuffer) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { status, events, sendMessage, clearEvents };
}
