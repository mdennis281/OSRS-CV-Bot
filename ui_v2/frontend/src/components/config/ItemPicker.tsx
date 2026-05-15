import { useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import type { ConfigWidgetProps, ItemValue } from '../../types/config';
import { searchItems } from '../../api/items';
import type { Item } from '../../types/item';
import ItemPropIcons from '../items/ItemPropIcons';

export default function ItemPicker({ name, value, onChange }: ConfigWidgetProps<ItemValue | null>) {
  const [showModal, setShowModal] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Item[]>([]);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); return; }
    const res = await searchItems({ q, limit: 20 });
    setResults(res.results);
  }, []);

  const select = (item: Item) => {
    onChange({
      id: item.id,
      name: item.name,
      icon_b64: item.icon_b64 ?? undefined,
      stackable: item.stackable,
      equipable: item.equipable,
      tradeable_on_ge: item.tradeable_on_ge,
      members: item.members,
      cost: item.cost,
      highalch: item.highalch,
      lowalch: item.lowalch,
    });
    setShowModal(false);
  };

  return (
    <div className="config-widget item-picker">
      <label>{name}</label>
      <div className="item-picker-display">
        {value ? (
          <div className="item-picker-selected">
            {value.icon_b64 && (
              <img src={`data:image/png;base64,${value.icon_b64}`} alt={value.name} />
            )}
            <span>{value.name}</span>
          </div>
        ) : (
          <span className="placeholder">No item selected</span>
        )}
        <button onClick={() => setShowModal(true)}>Browse</button>
      </div>

      {showModal && createPortal(
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="modal-content item-picker-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Select Item</h3>
              <button onClick={() => setShowModal(false)}>✕</button>
            </div>
            <input
              className="input item-picker-search"
              placeholder="Search items..."
              value={query}
              onChange={(e) => { setQuery(e.target.value); doSearch(e.target.value); }}
              autoFocus
            />
            <div className="item-picker-results">
              {query.trim() === '' ? (
                <div className="item-picker-empty">Search for an item above</div>
              ) : results.length === 0 ? (
                <div className="item-picker-empty">No results found for "{query}"</div>
              ) : (
                results.map((item) => (
                  <div key={item.id} className="item-picker-row" onClick={() => select(item)}>
                    {item.icon_b64 && (
                      <img src={`data:image/png;base64,${item.icon_b64}`} alt={item.name} />
                    )}
                    <span className="item-picker-name">{item.name}</span>
                    <ItemPropIcons item={item} />
                    <span className="item-id">#{item.id}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
