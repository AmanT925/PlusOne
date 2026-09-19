import { useCallback, useEffect, useRef } from 'react';
import type { ClientToServer, ServerToClient } from './types';

type Handlers = {
  onMessage: (msg: ServerToClient) => void;
  onStatus: (status: 'off' | 'connecting' | 'live' | 'error') => void;
};

export function usePlusOneSocket(
  url: string | null,
  enabled: boolean,
  handlers: Handlers,
) {
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    if (!enabled || !url) {
      handlersRef.current.onStatus('off');
      return;
    }
    handlersRef.current.onStatus('connecting');
    let closed = false;
    let socket: WebSocket;
    try {
      socket = new WebSocket(url);
    } catch {
      handlersRef.current.onStatus('error');
      return;
    }
    wsRef.current = socket;
    socket.onopen = () => {
      if (!closed) handlersRef.current.onStatus('live');
    };
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(String(event.data)) as ServerToClient;
        handlersRef.current.onMessage(data);
      } catch {
        // ignore malformed
      }
    };
    socket.onerror = () => handlersRef.current.onStatus('error');
    socket.onclose = () => {
      if (!closed) handlersRef.current.onStatus('error');
    };
    return () => {
      closed = true;
      wsRef.current = null;
      socket.close();
    };
  }, [url, enabled]);

  const send = useCallback((msg: ClientToServer) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(JSON.stringify(msg));
    return true;
  }, []);

  return send;
}

export function wsUrl(host: string, room: string, user: string): string {
  const trimmed = host.replace(/\/$/, '');
  const scheme = trimmed.startsWith('wss://') || trimmed.startsWith('ws://')
    ? trimmed
    : `ws://${trimmed}`;
  return `${scheme}/ws/${encodeURIComponent(room)}/${encodeURIComponent(user)}`;
}
