import type { BotStatus } from '../../types/bot';

const STATUS_DOT: Record<string, string> = {
  running: '#4caf50',
  paused: '#ffa726',
  terminated: '#ef5350',
  not_running: '#666',
};

export default function BotStatusBadge({ status }: { status: BotStatus | null }) {
  const label = status?.status ?? 'unknown';
  return (
    <span className="status-badge">
      <span className="status-dot" style={{ background: STATUS_DOT[label] ?? '#666' }} />
      {label.replace('_', ' ')}
    </span>
  );
}
