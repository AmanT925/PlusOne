import { useCallback, useEffect, useRef } from 'react';
import type { ClientToServer, ServerToClient } from './types';
import { wsUrl } from './http';

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
  const queueRef = useRef<ClientToServer[]>([]);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  const flush = (socket: WebSocket) => {
    while (queueRef.current.length && socket.readyState === WebSocket.OPEN) {
      const next = queueRef.current.shift();
      if (next) socket.send(JSON.stringify(next));
    }
  };

  useEffect(() => {
    if (!enabled || !url) {
      handlersRef.current.onStatus('off');
      queueRef.current = [];
      return;
    }

    let stopped = false;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let handshake: ReturnType<typeof setTimeout> | null = null;
    let ping: ReturnType<typeof setInterval> | null = null;
    let attempt = 0;
    let generation = 0;

    const clearTimers = () => {
      if (retry) clearTimeout(retry);
      if (handshake) clearTimeout(handshake);
      if (ping) clearInterval(ping);
      retry = null;
      handshake = null;
      ping = null;
    };

    const connect = () => {
      if (stopped) return;
      const gen = ++generation;
      clearTimers();
      handlersRef.current.onStatus('connecting');
      let socket: WebSocket;
      try {
        socket = new WebSocket(url);
      } catch {
        handlersRef.current.onStatus('error');
        return;
      }
      wsRef.current = socket;

      handshake = setTimeout(() => {
        if (gen !== generation || stopped) return;
        if (socket.readyState !== WebSocket.OPEN) socket.close();
      }, 10000);

      socket.onopen = () => {
        if (gen !== generation) {
          socket.close();
          return;
        }
        if (handshake) clearTimeout(handshake);
        attempt = 0;
        handlersRef.current.onStatus('live');
        flush(socket);
        ping = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: 'ping' }));
          }
        }, 15000);
      };
      socket.onmessage = (event) => {
        if (gen !== generation) return;
        try {
          const data = JSON.parse(String(event.data)) as ServerToClient;
          handlersRef.current.onMessage(data);
        } catch {
          // ignore malformed
        }
      };
      socket.onerror = () => {
        if (gen !== generation) return;
      };
      socket.onclose = () => {
        if (gen !== generation) return;
        clearTimers();
        if (wsRef.current === socket) wsRef.current = null;
        if (stopped) return;
        attempt += 1;
        handlersRef.current.onStatus(attempt > 2 ? 'error' : 'connecting');
        retry = setTimeout(connect, Math.min(800 * attempt, 4000));
      };
    };

    connect();
    return () => {
      stopped = true;
      generation += 1;
      clearTimers();
      const socket = wsRef.current;
      wsRef.current = null;
      if (socket && socket.readyState < WebSocket.CLOSING) socket.close();
    };
  }, [url, enabled]);

  const send = useCallback((msg: ClientToServer) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg));
      return true;
    }
    if (queueRef.current.length < 20) queueRef.current.push(msg);
    return true;
  }, []);

  return send;
}

export { wsUrl };
