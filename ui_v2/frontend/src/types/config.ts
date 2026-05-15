/** All 13 config parameter type definitions. */

// ---- Primitive wrappers (raw value in config JSON) ----

export type BooleanValue = boolean;
export type IntValue = number;
export type FloatValue = number;
export type StringValue = string;

// ---- Complex types (envelope { type, value }) ----

export interface RGBValue {
  rgb: [number, number, number];
  hex: string;
}

export type RangeValue = [number, number]; // [min, max]

export interface BreakCfgValue {
  break_duration: { type: 'Range'; value: RangeValue };
  break_chance: number;
}

export interface WaypointValue {
  x: number;
  y: number;
  z: number;
  chunk: number;
  tolerance: number;
}

export type RouteValue = { type: 'Waypoint'; value: WaypointValue }[];

export interface ItemValue {
  id: number;
  name: string;
  icon_b64?: string;
  stackable: boolean;
  equipable: boolean;
  tradeable_on_ge: boolean;
  members: boolean;
  cost: number;
  highalch: number;
  lowalch: number;
}

export type ItemListValue = { type: 'Item'; value: ItemValue }[];

export type StringListValue = string[];

export type RGBListValue = { type: 'RGB'; value: RGBValue }[];

// ---- Typed envelope used in API transport ----

export type ConfigParamType =
  | 'RGB'
  | 'Range'
  | 'BreakCfg'
  | 'Waypoint'
  | 'Route'
  | 'Item'
  | 'ItemList'
  | 'Boolean'
  | 'Int'
  | 'Float'
  | 'String'
  | 'StringList'
  | 'RGBList';

export interface ConfigParam {
  type: ConfigParamType;
  value: unknown;
  description?: string;
}

/**
 * A config record as stored/loaded by the API.
 * Keys are param names, values are either raw primitives or ConfigParam envelopes.
 */
export type BotConfig = Record<string, ConfigParam | boolean | number | string>;

// ---- Widget props shared by all config input components ----

export interface ConfigWidgetProps<V = unknown> {
  name: string;
  value: V;
  onChange: (value: V) => void;
  description?: string;
}
