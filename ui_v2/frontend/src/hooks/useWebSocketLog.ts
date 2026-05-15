import { useEffect, useRef, useState, useCallback } from 'react';

export interface LogEntry {
  type: 'log';
  timestamp: string;
  logger_name: string;
  level: string;
  message: string;
}

interface UseWebSocketLogOptions {
  /** Max entries kept in memory. Default 1000. */
  maxEntries?: number;
}

/**
 * Hook that connects to the WebSocket log bridge at /ws/logs,
 * manages subscriptions, and buffers log entries.
 */
export function useWebSocketLog(options: UseWebSocketLogOptions = {}) {
  const { maxEntries = 1000 } = options;
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [loggers, setLoggers] = useState<string[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>(null);

  const connect = useCallback(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/logs`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Request available loggers
      ws.send(JSON.stringify({ command: 'get_loggers' }));
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.type === 'log') {
          const entry = data as LogEntry;
          setEntries((prev) => {
            const next = [...prev, entry];
            return next.length > maxEntries ? next.slice(next.length - maxEntries) : next;
          });
          // Auto-include new logger sources as they appear
          if (entry.logger_name) {
            setLoggers((prev) =>
              prev.includes(entry.logger_name) ? prev : [...prev, entry.logger_name],
            );
          }
        } else if (data.type === 'loggers_list') {
          setLoggers(data.loggers ?? []);
        }
      } catch {
        // ignore malformed
      }
    };

    ws.onclose = () => {
      setConnected(false);
      // Auto-reconnect after 3 s
      reconnectTimer.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => ws.close();
  }, [maxEntries]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current ?? undefined);
      wsRef.current?.close();
    };
  }, [connect]);

  const subscribe = useCallback((loggerNames: string[] | null) => {
    wsRef.current?.send(
      JSON.stringify({ command: 'subscribe', loggers: loggerNames }),
    );
  }, []);

  const clearEntries = useCallback(() => setEntries([]), []);

  return { entries, loggers, connected, subscribe, clearEntries };
}
