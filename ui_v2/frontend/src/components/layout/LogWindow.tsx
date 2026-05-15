import { useState, useRef, useEffect, useCallback } from 'react';
import { useWebSocketLog } from '../../hooks/useWebSocketLog';
import { useLogWindow } from '../../contexts/LogWindowContext';

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: '#888',
  INFO: '#4fc3f7',
  WARNING: '#ffa726',
  ERROR: '#ef5350',
  CRITICAL: '#ff1744',
};

const MIN_W = 320;
const MIN_H = 180;

/**
 * Floating / draggable / resizable log window that persists across all pages.
 * Click the tab or sidebar "Logs" to open. Pulses if already open.
 * Resize from the bottom-right corner handle.
 */
export default function LogWindow() {
  const { entries, loggers, connected, subscribe, clearEntries } = useWebSocketLog();
  const { isOpen, pulse, openLog, closeLog } = useLogWindow();
  const [filter, setFilter] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [hiddenSources, setHiddenSources] = useState<Set<string>>(new Set());
  const [sourceDropOpen, setSourceDropOpen] = useState(false);
  const [levelDropOpen, setLevelDropOpen] = useState(false);
  const [position, setPosition] = useState({ x: 20, y: window.innerHeight - 360 });
  const [size, setSize] = useState({ w: 560, h: 320 });
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);
  const resizeRef = useRef<{ startX: number; startY: number; origW: number; origH: number } | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);
  const sourceDropRef = useRef<HTMLDivElement>(null);
  const levelDropRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries.length]);

  // Load saved prefs
  useEffect(() => {
    try {
      const saved = localStorage.getItem('logWindowPrefs');
      if (saved) {
        const prefs = JSON.parse(saved);
        if (prefs.position) setPosition(prefs.position);
        if (prefs.size) setSize(prefs.size);
        if (prefs.hiddenSources) setHiddenSources(new Set(prefs.hiddenSources));
      }
    } catch { /* ignore */ }
  }, []);

  // Save prefs
  useEffect(() => {
    localStorage.setItem('logWindowPrefs', JSON.stringify({
      position, size, hiddenSources: [...hiddenSources],
    }));
  }, [position, size, hiddenSources]);

  const toggleSource = useCallback((name: string) => {
    setHiddenSources((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }, []);

  // Close dropdowns on outside click
  useEffect(() => {
    if (!sourceDropOpen && !levelDropOpen) return;
    const handler = (e: MouseEvent) => {
      if (sourceDropOpen && sourceDropRef.current && !sourceDropRef.current.contains(e.target as Node)) {
        setSourceDropOpen(false);
      }
      if (levelDropOpen && levelDropRef.current && !levelDropRef.current.contains(e.target as Node)) {
        setLevelDropOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [sourceDropOpen, levelDropOpen]);

  // --- Drag header ---
  const onDragStart = useCallback((e: React.MouseEvent) => {
    dragRef.current = { startX: e.clientX, startY: e.clientY, origX: position.x, origY: position.y };
    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      setPosition({
        x: dragRef.current.origX + (ev.clientX - dragRef.current.startX),
        y: dragRef.current.origY + (ev.clientY - dragRef.current.startY),
      });
    };
    const onUp = () => {
      dragRef.current = null;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [position]);

  // --- Resize handle ---
  const onResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    resizeRef.current = { startX: e.clientX, startY: e.clientY, origW: size.w, origH: size.h };
    const onMove = (ev: MouseEvent) => {
      if (!resizeRef.current) return;
      setSize({
        w: Math.max(MIN_W, resizeRef.current.origW + (ev.clientX - resizeRef.current.startX)),
        h: Math.max(MIN_H, resizeRef.current.origH + (ev.clientY - resizeRef.current.startY)),
      });
    };
    const onUp = () => {
      resizeRef.current = null;
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  }, [size]);

  const filtered = entries.filter((e) => {
    if (hiddenSources.has(e.logger_name)) return false;
    if (filter && !e.logger_name.toLowerCase().includes(filter.toLowerCase()) && !e.message.toLowerCase().includes(filter.toLowerCase())) return false;
    if (levelFilter && e.level !== levelFilter) return false;
    return true;
  });

  const connDot = <span className={`log-dot ${connected ? 'connected' : ''}`} />;

  if (!isOpen) {
    return (
      <button className="log-tab" onClick={openLog}>
        Logs {connDot} ({entries.length})
      </button>
    );
  }

  const cls = ['log-window', pulse && 'pulse'].filter(Boolean).join(' ');

  return (
    <div
      className={cls}
      style={{ left: position.x, top: position.y, width: size.w, height: size.h }}
    >
      <div className="log-window-header" onMouseDown={onDragStart}>
        <span className="log-window-title">Logs {connDot}</span>
        <div className="log-window-actions">
          <button onClick={clearEntries} title="Clear">✕</button>
          <button onClick={closeLog} title="Close">_</button>
        </div>
      </div>

      <div className="log-window-filters">
        <input
          placeholder="Filter..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />

        {/* Level dropdown */}
        <div className="log-dropdown" ref={levelDropRef}>
          <button
            className="log-dropdown-trigger"
            onClick={() => { setLevelDropOpen((v) => !v); setSourceDropOpen(false); }}
          >
            {levelFilter || 'All Levels'}
            <span className="log-dropdown-caret">{levelDropOpen ? '▲' : '▼'}</span>
          </button>
          {levelDropOpen && (
            <div className="log-dropdown-menu">
              <button
                className={`log-dropdown-item ${!levelFilter ? 'selected' : ''}`}
                onClick={() => { setLevelFilter(''); setLevelDropOpen(false); }}
              >
                All Levels
              </button>
              {['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map((l) => (
                <button
                  key={l}
                  className={`log-dropdown-item ${levelFilter === l ? 'selected' : ''}`}
                  onClick={() => { setLevelFilter(l); setLevelDropOpen(false); }}
                >
                  <span className="log-level-dot" style={{ background: LEVEL_COLORS[l] }} />
                  {l}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Source dropdown */}
        {loggers.length > 0 && (
          <div className="log-dropdown" ref={sourceDropRef}>
            <button
              className="log-dropdown-trigger"
              onClick={() => { setSourceDropOpen((v) => !v); setLevelDropOpen(false); }}
            >
              Sources ({loggers.length - hiddenSources.size}/{loggers.length})
              <span className="log-dropdown-caret">{sourceDropOpen ? '▲' : '▼'}</span>
            </button>
            {sourceDropOpen && (
              <div className="log-dropdown-menu">
                <button
                  className="log-dropdown-item"
                  onClick={() => {
                    if (hiddenSources.size === 0) setHiddenSources(new Set(loggers));
                    else setHiddenSources(new Set());
                  }}
                >
                  <span className={`log-dropdown-check ${hiddenSources.size === 0 ? 'checked' : ''}`} />
                  All
                </button>
                <div className="log-dropdown-divider" />
                {loggers.map((name) => (
                  <button
                    key={name}
                    className="log-dropdown-item"
                    onClick={() => toggleSource(name)}
                  >
                    <span className={`log-dropdown-check ${!hiddenSources.has(name) ? 'checked' : ''}`} />
                    {name}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="log-window-body">
        {filtered.map((entry, i) => (
          <div key={i} className="log-entry" style={{ color: LEVEL_COLORS[entry.level] ?? '#ccc' }}>
            <span className="log-ts">{entry.timestamp}</span>
            <span className="log-logger">[{entry.logger_name}]</span>
            <span className="log-level">{entry.level}</span>
            <span className="log-msg">{entry.message}</span>
          </div>
        ))}
        <div ref={logEndRef} />
      </div>

      {/* Resize handle — bottom-right corner */}
      <div className="log-window-resize" onMouseDown={onResizeStart} />
    </div>
  );
}
