import { useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import type { ConfigWidgetProps, ItemListValue, ItemValue } from '../../types/config';
import { searchItems } from '../../api/items';
import type { Item } from '../../types/item';
import ItemPropIcons from '../items/ItemPropIcons';

export default function ItemListPicker({ name, value, onChange }: ConfigWidgetProps<ItemListValue>) {
  const items = value ?? [];
  const [showModal, setShowModal] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Item[]>([]);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); return; }
    const res = await searchItems({ q, limit: 20 });
    setResults(res.results);
  }, []);

  const addItem = (item: Item) => {
    const itemValue: ItemValue = {
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
    };
    onChange([...items, { type: 'Item', value: itemValue }]);
    setShowModal(false);
    setQuery('');
    setResults([]);
  };

  const removeItem = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  return (
    <div className="config-widget item-list-picker">
      <label>{name}</label>
      <div className="item-list">
        {items.map((entry, i) => (
          <div key={i} className="item-list-row">
            {entry.value.icon_b64 && (
              <img src={`data:image/png;base64,${entry.value.icon_b64}`} alt={entry.value.name} />
            )}
            <span>{entry.value.name}</span>
            <button className="remove-btn" onClick={() => removeItem(i)}>✕</button>
          </div>
        ))}
      </div>
      <button className="add-btn" onClick={() => setShowModal(true)}>+ Add Item</button>

      {showModal && createPortal(
        <div className="modal-backdrop" onClick={() => setShowModal(false)}>
          <div className="modal-content item-picker-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add Item</h3>
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
                  <div key={item.id} className="item-picker-row" onClick={() => addItem(item)}>
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
