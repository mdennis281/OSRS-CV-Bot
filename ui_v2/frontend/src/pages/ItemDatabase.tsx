import { useState, useCallback } from 'react';
import { searchItems, fetchItemDetail } from '../api/items';
import type { ItemSearchParams } from '../api/items';
import type { Item } from '../types/item';
import ItemSearchBar from '../components/items/ItemSearchBar';
import ItemCard from '../components/items/ItemCard';
import ItemDetailModal from '../components/items/ItemDetailModal';

export default function ItemDatabase() {
  const [items, setItems] = useState<Item[]>([]);
  const [detail, setDetail] = useState<Item | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = useCallback(async (params: ItemSearchParams) => {
    if (!params.q.trim()) { setItems([]); return; }
    setLoading(true);
    try {
      const res = await searchItems({ ...params, limit: 50 });
      setItems(res.results);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, []);

  const openDetail = async (id: number) => {
    try {
      const res = await fetchItemDetail(id);
      if (res.item) setDetail(res.item);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="page item-database">
      <header className="page-header">
        <h1>Item Database</h1>
      </header>
      <ItemSearchBar onSearch={handleSearch} />
      {loading && <p className="loading-text">Searching...</p>}
      <section className="item-grid">
        {items.map((item) => (
          <ItemCard key={item.id} item={item} onClick={() => openDetail(item.id)} />
        ))}
        {!loading && items.length === 0 && <p className="empty">Search for items above.</p>}
      </section>
      {detail && <ItemDetailModal item={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}
