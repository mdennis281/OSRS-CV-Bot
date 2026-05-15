import { useState, useEffect, useRef } from 'react';
import type { ItemSearchParams } from '../../api/items';

interface ItemSearchBarProps {
  onSearch: (params: ItemSearchParams) => void;
  debounceMs?: number;
}

export default function ItemSearchBar({ onSearch, debounceMs = 300 }: ItemSearchBarProps) {
  const [query, setQuery] = useState('');
  const [tradeable, setTradeable] = useState(false);
  const [members, setMembers] = useState(false);
  const [equipable, setEquipable] = useState(false);
  const [stackable, setStackable] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>(null);

  useEffect(() => {
    clearTimeout(timer.current ?? undefined);
    timer.current = setTimeout(() => {
      onSearch({
        q: query,
        tradeable: tradeable || undefined,
        members: members || undefined,
        equipable: equipable || undefined,
        stackable: stackable || undefined,
      });
    }, debounceMs);
    return () => clearTimeout(timer.current ?? undefined);
  }, [query, tradeable, members, equipable, stackable, debounceMs, onSearch]);

  return (
    <div className="item-search-bar">
      <input
        type="text"
        placeholder="Search items..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="search-filters">
        <button
          className={`filter-tag ${tradeable ? 'active' : ''}`}
          onClick={() => setTradeable(!tradeable)}
        >
          Tradeable
        </button>
        <button
          className={`filter-tag ${members ? 'active' : ''}`}
          onClick={() => setMembers(!members)}
        >
          Members
        </button>
        <button
          className={`filter-tag ${equipable ? 'active' : ''}`}
          onClick={() => setEquipable(!equipable)}
        >
          Equipable
        </button>
        <button
          className={`filter-tag ${stackable ? 'active' : ''}`}
          onClick={() => setStackable(!stackable)}
        >
          Stackable
        </button>
      </div>
    </div>
  );
}
