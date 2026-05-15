import { useEffect, useRef, useState } from 'react';

export interface MatchItem {
  id: number;
  timestamp: string;
  confidence: number;
  scale: number;
  bbox: [number, number, number, number];
  images: {
    template: string;
    parent_annotated: string;
  };
}

/**
 * Hook that subscribes to the CV debug SSE stream via /api/cv-debug/stream.
 * Only opens the connection when `enabled` is true.
 */
export function useCvDebug(enabled: boolean) {
  const [items, setItems] = useState<MatchItem[]>([]);
  const [connected, setConnected] = useState(false);
  const esRef = useRef<EventSource | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!enabled) {
      // Tear down any existing connection
      if (reconnectTimer.current) { clearTimeout(reconnectTimer.current); reconnectTimer.current = null; }
      if (esRef.current) { esRef.current.close(); esRef.current = null; }
      setConnected(false);
      return;
    }

    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      const es = new EventSource('/api/cv-debug/stream');
      esRef.current = es;

      es.onopen = () => { if (!cancelled) setConnected(true); };

      es.onmessage = (evt) => {
        try {
          const data = JSON.parse(evt.data);
          if (data.type === 'match' && data.item) {
            setItems((prev) => {
              const next = [data.item as MatchItem, ...prev];
              return next.length > 20 ? next.slice(0, 20) : next;
            });
          }
        } catch {
          // ignore
        }
      };

      es.onerror = () => {
        if (!cancelled) setConnected(false);
        es.close();
        if (!cancelled) {
          reconnectTimer.current = setTimeout(connect, 3000);
        }
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer.current) { clearTimeout(reconnectTimer.current); reconnectTimer.current = null; }
      if (esRef.current) { esRef.current.close(); esRef.current = null; }
      setConnected(false);
    };
  }, [enabled]);

  return { items, connected };
}
