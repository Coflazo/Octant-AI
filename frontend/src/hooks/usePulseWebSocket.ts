import { useState, useEffect, useCallback, useRef } from 'react';

export interface PulseEvent {
    type: string;
    payload: any;
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
        const ws = new WebSocket(`ws://localhost:8000/ws/${sessionId}`);
        
        ws.onopen = () => {
            setStatus("connected");
            retryCount.current = 0;
            console.log("WebSocket connected.");
        };
        
        ws.onmessage = (msg) => {
            try {
                const data = JSON.parse(msg.data);
                setEvents(prev => [...prev, data]);
            } catch (e) {
                console.warn("Non-JSON message received over WS", msg.data);
            }
        };
        
        ws.onclose = () => {
            setStatus("disconnected");
            if (retryCount.current < maxRetries) {
                const delay = Math.pow(2, retryCount.current) * 1000;
                retryCount.current += 1;
                console.log(`WS Reconnecting in ${delay}ms... (Attempt ${retryCount.current})`);
                setTimeout(connect, delay);
            } else {
                setStatus("error");
            }
        };
        
        ws.onerror = (err) => {
            console.error("WebSocket error:", err);
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
        } else {
            console.warn("Cannot send, WebSocket not open.");
        }
    }, []);

    const clearEvents = useCallback(() => setEvents([]), []);

    return { status, events, sendMessage, clearEvents };
}
