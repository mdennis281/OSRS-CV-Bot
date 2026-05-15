import { useEffect, useState, useCallback } from 'react';
import { fetchBots, fetchAllStatuses, controlBot, stopBot } from '../api/bots';
import type { BotInfo, BotStatus } from '../types/bot';
import BotStatusBadge from '../components/bots/BotStatusBadge';
import CvDebugViewer from '../components/cv-debug/CvDebugViewer';

type Tab = 'status' | 'cv-debug' | 'log';

export default function RunningBot() {
  const [bots, setBots] = useState<BotInfo[]>([]);
  const [statuses, setStatuses] = useState<Record<string, BotStatus>>({});
  const [tab, setTab] = useState<Tab>('status');

  const refresh = useCallback(async () => {
    try {
      const [reg, sts] = await Promise.all([fetchBots(), fetchAllStatuses()]);
      setBots(Object.values(reg));
      setStatuses(sts);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  }, [refresh]);

  const running = bots.filter((b) => {
    const s = statuses[b.id]?.status;
    return s === 'running' || s === 'paused';
  });

  const handleControl = async (botId: string, action: 'pause' | 'resume' | 'terminate') => {
    await controlBot(botId, { action });
    refresh();
  };

  const handleStop = async (botId: string) => {
    await stopBot(botId);
    refresh();
  };

  return (
    <div className="page running-bot">
      <header className="page-header">
        <h1>Running Bots</h1>
        <div className="tab-bar">
          {(['status', 'cv-debug', 'log'] as const).map((t) => (
            <button
              key={t}
              className={`tab ${tab === t ? 'active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t === 'cv-debug' ? 'CV Debug' : t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </header>

      {tab === 'status' && (
        <section className="running-list">
          {running.length === 0 && <p className="empty">No bots currently running.</p>}
          {running.map((bot) => {
            const s = statuses[bot.id];
            return (
              <div key={bot.id} className="running-card card">
                <div className="running-card-header">
                  <h2>{bot.name}</h2>
                  <BotStatusBadge status={s ?? null} />
                </div>
                {s?.runtime_formatted && <p className="runtime">Runtime: {s.runtime_formatted}</p>}
                <div className="running-actions">
                  {s?.status === 'running' && (
                    <button onClick={() => handleControl(bot.id, 'pause')}>Pause</button>
                  )}
                  {s?.status === 'paused' && (
                    <button onClick={() => handleControl(bot.id, 'resume')}>Resume</button>
                  )}
                  <button className="danger" onClick={() => handleStop(bot.id)}>Stop</button>
                </div>
              </div>
            );
          })}
        </section>
      )}

      {tab === 'cv-debug' && (
        <section className="cv-debug-section">
          <CvDebugViewer />
        </section>
      )}

      {tab === 'log' && (
        <section className="log-section">
          <p>Log streaming is shown in the floating log window below.</p>
        </section>
      )}
    </div>
  );
}
