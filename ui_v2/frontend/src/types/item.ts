/** OSRS item as returned by the API. */
export interface Item {
  id: number;
  name: string;
  tradeable_on_ge: boolean;
  members: boolean;
  noted: boolean;
  noteable: boolean;
  placeholder?: boolean;
  stackable: boolean;
  equipable: boolean;
  cost: number;
  lowalch: number;
  highalch: number;
  icon_b64?: string | null;
}

export interface ItemSearchResponse {
  success: boolean;
  results: Item[];
  count: number;
}

export interface ItemDetailResponse {
  success: boolean;
  item?: Item;
  error?: string;
}
