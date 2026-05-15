import { createPortal } from 'react-dom';
import type { Item } from '../../types/item';

interface Props {
  item: Item | null;
  onClose: () => void;
}

function formatGp(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return String(value);
}

export default function ItemDetailModal({ item, onClose }: Props) {
  if (!item) return null;

  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{item.name}</h2>
          <button onClick={onClose}>✕</button>
        </div>

        <div className="item-detail-body">
          {item.icon_b64 && (
            <img
              className="item-detail-icon"
              src={`data:image/png;base64,${item.icon_b64}`}
              alt={item.name}
            />
          )}

          <table className="item-detail-table">
            <tbody>
              <tr><td>ID</td><td>{item.id}</td></tr>
              <tr><td>Cost</td><td>{formatGp(item.cost)} gp</td></tr>
              <tr><td>High Alch</td><td>{formatGp(item.highalch)} gp</td></tr>
              <tr><td>Low Alch</td><td>{formatGp(item.lowalch)} gp</td></tr>
              <tr><td>Members</td><td>{item.members ? 'Yes' : 'No'}</td></tr>
              <tr><td>Tradeable</td><td>{item.tradeable_on_ge ? 'Yes' : 'No'}</td></tr>
              <tr><td>Stackable</td><td>{item.stackable ? 'Yes' : 'No'}</td></tr>
              <tr><td>Equipable</td><td>{item.equipable ? 'Yes' : 'No'}</td></tr>
              <tr><td>Noted</td><td>{item.noted ? 'Yes' : 'No'}</td></tr>
              <tr><td>Noteable</td><td>{item.noteable ? 'Yes' : 'No'}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>,
    document.body,
  );
}
