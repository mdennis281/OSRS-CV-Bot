import { apiFetch } from './client';
import type {
  BotRegistry,
  BotStatus,
  BotStartRequest,
  BotControlRequest,
  SuccessResponse,
} from '../types/bot';
import type { ConfigParam } from '../types/config';

export function fetchBots(): Promise<BotRegistry> {
  return apiFetch<BotRegistry>('/api/bots');
}

/** Fetch status for all bots in a single request. */
export function fetchAllStatuses(): Promise<Record<string, BotStatus>> {
  return apiFetch<Record<string, BotStatus>>('/api/bots/status');
}

export function startBot(botId: string, body: BotStartRequest): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/api/bot/${botId}/start`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function stopBot(botId: string): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/api/bot/${botId}/stop`, { method: 'POST' });
}

export function controlBot(botId: string, body: BotControlRequest): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/api/bot/${botId}/control`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function fetchBotConfig(botId: string): Promise<Record<string, ConfigParam>> {
  return apiFetch<Record<string, ConfigParam>>(`/api/bot/${botId}/config`);
}

export function saveBotConfig(
  botId: string,
  config: Record<string, unknown>,
): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/api/bot/${botId}/config`, {
    method: 'POST',
    body: JSON.stringify(config),
  });
}

export function resetBotConfig(botId: string): Promise<SuccessResponse> {
  return apiFetch<SuccessResponse>(`/api/bot/${botId}/reset`, { method: 'POST' });
}
