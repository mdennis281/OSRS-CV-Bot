import { useState, useEffect } from 'react';
import type { ConfigParam, ConfigWidgetProps } from '../../types/config';
import { fetchBotConfig, saveBotConfig, resetBotConfig } from '../../api/bots';
import BooleanInput from './BooleanInput';
import IntInput from './IntInput';
import FloatInput from './FloatInput';
import StringInput from './StringInput';
import StringListInput from './StringListInput';
import RGBInput from './RGBInput';
import RGBListInput from './RGBListInput';
import RangeInput from './RangeInput';
import BreakCfgInput from './BreakCfgInput';
import ItemPicker from './ItemPicker';
import ItemListPicker from './ItemListPicker';
import RoutePicker from './RoutePicker';

type WidgetComponent = React.ComponentType<ConfigWidgetProps<any>>;

const WIDGET_MAP: Record<string, WidgetComponent> = {
  Boolean: BooleanInput,
  Int: IntInput,
  Float: FloatInput,
  String: StringInput,
  StringList: StringListInput,
  RGB: RGBInput,
  RGBList: RGBListInput,
  Range: RangeInput,
  BreakCfg: BreakCfgInput,
  Item: ItemPicker,
  ItemList: ItemListPicker,
  Route: RoutePicker,
};

interface ParamEntry {
  name: string;
  type: string;
  value: unknown;
  description?: string;
}

interface ConfigFormProps {
  botId: string;
}

export default function ConfigForm({ botId }: ConfigFormProps) {
  const [params, setParams] = useState<ParamEntry[]>([]);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = async () => {
    try {
      const data = await fetchBotConfig(botId);
      const entries: ParamEntry[] = Object.entries(data).map(([name, param]) => ({
        name,
        type: param.type,
        value: param.value,
        description: param.description,
      }));
      setParams(entries);
      setDirty(false);
      setError(null);
    } catch (e: any) {
      setError(e.message ?? 'Failed to load config');
    }
  };

  useEffect(() => { load(); }, [botId]);

  const updateParam = (index: number, newValue: any) => {
    setParams((prev) =>
      prev.map((p, i) => (i === index ? { ...p, value: newValue } : p)),
    );
    setDirty(true);
    setSuccess(null);
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const payload = Object.fromEntries(
        params.map((p) => [p.name, { type: p.type, value: p.value }]),
      );
      await saveBotConfig(botId, payload);
      setDirty(false);
      setSuccess('Config saved.');
      setTimeout(() => setSuccess(null), 2000);
    } catch (e: any) {
      setError(e.message ?? 'Failed to save config');
    } finally {
      setSaving(false);
    }
  };

  const reset = async () => {
    try {
      await resetBotConfig(botId);
      await load();
      setSuccess('Config reset to defaults.');
      setTimeout(() => setSuccess(null), 2000);
    } catch (e: any) {
      setError(e.message ?? 'Failed to reset config');
    }
  };

  const exportConfig = () => {
    const blob = new Blob([JSON.stringify(params, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${botId}_config.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const importConfig = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      const text = await file.text();
      try {
        const imported = JSON.parse(text) as ParamEntry[];
        setParams(imported);
        setDirty(true);
      } catch {
        setError('Invalid JSON in imported file');
      }
    };
    input.click();
  };

  return (
    <div className="config-form">
      {error && <div className="config-error">{error}</div>}
      {success && <div className="config-success">{success}</div>}

      <div className="config-params">
        {params.map((param, index) => {
          const Widget = WIDGET_MAP[param.type];
          if (!Widget) {
            return (
              <div key={param.name} className="config-widget unsupported">
                <label>{param.name}</label>
                <span className="unsupported-tag">Unsupported type: {param.type}</span>
              </div>
            );
          }
          return (
            <Widget
              key={param.name}
              name={param.name}
              value={param.value}
              onChange={(v) => updateParam(index, v)}
              description={param.description}
            />
          );
        })}
        {params.length === 0 && <p className="no-params">No config parameters.</p>}
      </div>

      <div className="config-actions">
        <button onClick={save} disabled={!dirty || saving}>
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button onClick={reset} className="secondary">Reset</button>
        <button onClick={exportConfig} className="secondary">Export</button>
        <button onClick={importConfig} className="secondary">Import</button>
      </div>
    </div>
  );
}
