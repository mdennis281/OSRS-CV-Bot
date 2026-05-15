import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { fetchBots } from '../../api/bots';
import type { BotRegistry } from '../../types/bot';
import TierBadge from '../bots/TierBadge';
import { useLogWindow } from '../../contexts/LogWindowContext';

const tierOrder: Record<string, number> = { S: 0, A: 1, B: 2, C: 3, D: 4, '?': 5 };

export default function Sidebar() {
  const [bots, setBots] = useState<BotRegistry>({});
  const [collapsed, setCollapsed] = useState(false);
  const { openLog } = useLogWindow();

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetchBots()
        .then((reg) => {
          if (!cancelled) setBots(reg);
        })
        .catch(() => {
          // Backend not ready yet — retry in 2 s
          if (!cancelled) setTimeout(load, 2000);
        });
    };
    load();
    return () => { cancelled = true; };
  }, []);

  const sorted = Object.values(bots).sort(
    (a, b) => (tierOrder[a.tier] ?? 5) - (tierOrder[b.tier] ?? 5),
  );

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        {!collapsed && <h2>OSRS Bots</h2>}
        <button className="collapse-btn" onClick={() => setCollapsed(!collapsed)}>
          {collapsed ? '»' : '«'}
        </button>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" className="nav-link" end>
          {collapsed ? '🏠' : 'Dashboard'}
        </NavLink>
        <NavLink to="/running" className="nav-link">
          {collapsed ? '▶' : 'Running Bot'}
        </NavLink>
        <NavLink to="/items" className="nav-link">
          {collapsed ? '🎒' : 'Item Database'}
        </NavLink>
        <button className="nav-link log-nav-btn" onClick={openLog}>
          {collapsed ? '📋' : 'Logs'}
        </button>

        <hr />

        {sorted.map((bot) => (
          <NavLink key={bot.id} to={`/bot/${bot.id}`} className="nav-link bot-link">
            {!collapsed && <TierBadge tier={bot.tier} />}
            <span className="bot-name">{collapsed ? bot.name[0] : bot.name}</span>
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
