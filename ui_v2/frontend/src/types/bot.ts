import type { BotConfig, ConfigParam } from './config';

/** Bot info as returned by GET /api/bots */
export interface BotInfo {
  id: string;
  name: string;
  description: string;
  instructions: string;
  tier: string;
  file_path: string;
  module_name: string;
  config_params: Record<string, ConfigParam>;
  default_config: Record<string, unknown>;
}

/** Maps bot_id → BotInfo */
export type BotRegistry = Record<string, BotInfo>;

/** GET /api/bot/{id}/status */
export interface BotStatus {
  status: 'running' | 'paused' | 'terminated' | 'not_running';
  paused?: boolean;
  runtime?: number;
  runtime_formatted?: string;
  start_time?: number;
}

/** POST /api/bot/{id}/start body */
export interface BotStartRequest {
  config: Record<string, unknown>;
  username: string;
}

/** POST /api/bot/{id}/control body */
export interface BotControlRequest {
  action: 'pause' | 'resume' | 'terminate';
  value?: unknown;
}

/** Generic success response */
export interface SuccessResponse {
  success: boolean;
  error?: string;
}
