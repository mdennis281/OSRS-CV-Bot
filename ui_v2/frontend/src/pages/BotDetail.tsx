import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchBots, startBot, fetchAllStatuses } from '../api/bots';
import type { BotInfo, BotStatus } from '../types/bot';
import ConfigForm from '../components/config/ConfigForm';
import BotStatusBadge from '../components/bots/BotStatusBadge';
import TierBadge from '../components/bots/TierBadge';

export default function BotDetail() {
  const { botId } = useParams<{ botId: string }>();
  const navigate = useNavigate();
  const [bot, setBot] = useState<BotInfo | null>(null);
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [username, setUsername] = useState('');
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!botId) return;
    let cancelled = false;
    const load = () => {
      Promise.all([fetchBots(), fetchAllStatuses()])
        .then(([reg, sts]) => {
          if (cancelled) return;
          setBot(reg[botId] ?? null);
          setStatus(sts[botId] ?? null);
        })
        .catch(() => {
          // Backend not ready yet — retry in 2 s
          if (!cancelled) setTimeout(load, 2000);
        });
    };
    load();
    return () => { cancelled = true; };
  }, [botId]);

  const handleStart = async () => {
    if (!botId) return;
    setStarting(true);
    setError(null);
    try {
      const res = await startBot(botId, { config: {}, username });
      if (!res.success) throw new Error(res.error ?? 'Start failed');
      navigate('/running');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setStarting(false);
    }
  };

  if (!bot) return <div className="page loading">Loading...</div>;

  const isRunning = status?.status === 'running' || status?.status === 'paused';

  return (
    <div className="page bot-detail">
      <header className="page-header">
        <div className="bot-title">
          <h1>{bot.name}</h1>
          <TierBadge tier={bot.tier} />
          {status && <BotStatusBadge status={status} />}
        </div>
        <p className="description">{bot.description}</p>
      </header>

      {bot.instructions && (
        <section className="instructions card">
          <h2>Instructions</h2>
          <pre>{bot.instructions}</pre>
        </section>
      )}

      <section className="config-section card">
        <h2>Configuration</h2>
        <ConfigForm botId={bot.id} />
      </section>

      <section className="start-section card">
        <h2>Start Bot</h2>
        <div className="start-controls">
          <input
            placeholder="Username (optional)"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <button onClick={handleStart} disabled={starting || isRunning}>
            {starting ? 'Starting...' : isRunning ? 'Already Running' : 'Start'}
          </button>
        </div>
        {error && <div className="start-error">{error}</div>}
      </section>
    </div>
  );
}
