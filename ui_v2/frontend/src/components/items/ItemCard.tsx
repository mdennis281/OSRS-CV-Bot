import type { Item } from '../../types/item';
import ItemPropIcons from './ItemPropIcons';

interface Props {
  item: Item;
  onClick?: () => void;
}

export default function ItemCard({ item, onClick }: Props) {
  return (
    <div className="item-card" onClick={onClick} tabIndex={0} role="button">
      <div className="item-card-top">
        {item.icon_b64 && (
          <img
            className="item-icon"
            src={`data:image/png;base64,${item.icon_b64}`}
            alt={item.name}
          />
        )}
        <div className="item-info">
          <span className="item-name">{item.name}</span>
          <span className="item-id">#{item.id}</span>
        </div>
      </div>
      <div className="item-tags">
        <ItemPropIcons item={item} />
      </div>
    </div>
  );
}
