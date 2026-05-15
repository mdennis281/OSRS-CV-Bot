import { useEffect, useState } from 'react';
import { fetchBots } from '../api/bots';
import type { BotInfo } from '../types/bot';
import BotCard from '../components/bots/BotCard';

const TIER_ORDER: Record<string, number> = { S: 0, A: 1, B: 2, C: 3, D: 4 };

export default function Dashboard() {
  const [bots, setBots] = useState<BotInfo[]>([]);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetchBots()
        .then((reg) => {
          if (!cancelled) setBots(Object.values(reg));
        })
        .catch(() => {
          // Backend not ready yet — retry in 2 s
          if (!cancelled) setTimeout(load, 2000);
        });
    };
    load();
    return () => { cancelled = true; };
  }, []);

  const sorted = [...bots].sort((a, b) => {
    const ta = TIER_ORDER[a.tier] ?? 99;
    const tb = TIER_ORDER[b.tier] ?? 99;
    return ta - tb || a.name.localeCompare(b.name);
  });

  const filtered = filter
    ? sorted.filter((b) => b.name.toLowerCase().includes(filter.toLowerCase()))
    : sorted;

  return (
    <div className="page dashboard">
      <header className="page-header">
        <h1>Dashboard</h1>
        <input
          className="search-input"
          placeholder="Filter bots..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
      </header>
      <section className="bot-grid">
        {filtered.map((bot) => (
          <BotCard key={bot.id} bot={bot} />
        ))}
        {filtered.length === 0 && <p className="empty">No bots found.</p>}
      </section>
    </div>
  );
}
