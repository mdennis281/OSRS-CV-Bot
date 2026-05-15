import { apiFetch } from './client';
import type { ItemSearchResponse, ItemDetailResponse } from '../types/item';

export interface ItemSearchParams {
  q: string;
  limit?: number;
  tradeable?: boolean;
  members?: boolean;
  stackable?: boolean;
  equipable?: boolean;
}

export function searchItems(params: ItemSearchParams): Promise<ItemSearchResponse> {
  const sp = new URLSearchParams();
  sp.set('q', params.q);
  if (params.limit) sp.set('limit', String(params.limit));
  if (params.tradeable) sp.set('tradeable', 'true');
  if (params.members) sp.set('members', 'true');
  if (params.stackable) sp.set('stackable', 'true');
  if (params.equipable) sp.set('equipable', 'true');
  return apiFetch<ItemSearchResponse>(`/api/items/search?${sp}`);
}

export function fetchItemDetail(itemId: number): Promise<ItemDetailResponse> {
  return apiFetch<ItemDetailResponse>(`/api/items/${itemId}`);
}
