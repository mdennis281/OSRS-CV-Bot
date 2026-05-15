import { Link } from 'react-router-dom';
import type { BotInfo } from '../../types/bot';
import TierBadge from './TierBadge';

export default function BotCard({ bot }: { bot: BotInfo }) {
  return (
    <Link to={`/bot/${bot.id}`} className="bot-card">
      <div className="card">
        <div className="bot-card-header">
          <TierBadge tier={bot.tier} />
          <h3>{bot.name}</h3>
        </div>
        {bot.description && <p className="bot-card-desc">{bot.description}</p>}
      </div>
    </Link>
  );
}
