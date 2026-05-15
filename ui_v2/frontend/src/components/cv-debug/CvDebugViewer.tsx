import { useState, useEffect } from 'react';
import { useCvDebug } from '../../hooks/useCvDebug';
import { apiFetch } from '../../api/client';

export default function CvDebugViewer() {
  const [enabled, setEnabled] = useState(false);
  const { items, connected } = useCvDebug(enabled);

  useEffect(() => {
    apiFetch<{ enabled: boolean }>('/api/cv-debug/status')
      .then((res) => setEnabled(res.enabled))
      .catch(() => {});
  }, []);

  const toggle = async () => {
    const next = !enabled;
    try {
      await apiFetch('/api/cv-debug/toggle', {
        method: 'POST',
        body: JSON.stringify({ enabled: next }),
      });
      setEnabled(next);
    } catch {
      // failed
    }
  };

  return (
    <div className="cv-debug-viewer">
      <div className="cv-debug-header">
        <h3>CV Debug</h3>
        <span className={`status-dot ${connected ? 'connected' : ''}`} />
        <button className={`toggle-btn ${enabled ? 'active' : ''}`} onClick={toggle}>
          {enabled ? 'Disable' : 'Enable'}
        </button>
      </div>

      {!enabled && (
        <p className="cv-debug-notice">
          CV Debug is off by default. Enable to view template matches (has performance impact).
        </p>
      )}

      {enabled && items.length === 0 && (
        <p className="cv-debug-notice">Waiting for matches…</p>
      )}

      <div className="cv-debug-grid">
        {items.map((item) => (
          <div key={item.id} className="cv-debug-card">
            <div className="cv-debug-meta">
              <span className="tag">t={item.timestamp}</span>
              <span className="tag">conf={item.confidence.toFixed(4)}</span>
              <span className="tag">scale={item.scale}</span>
              <span className="tag">bbox=[{item.bbox.join(', ')}]</span>
            </div>
            <div className="cv-debug-images">
              <img src={item.images.template} alt="template" />
              <img src={item.images.parent_annotated} alt="annotated" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
