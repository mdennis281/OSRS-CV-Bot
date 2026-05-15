import type { ConfigWidgetProps, BooleanValue } from '../../types/config';

export default function BooleanInput({ name, value, onChange }: ConfigWidgetProps<BooleanValue>) {
  return (
    <div className="config-widget boolean-input">
      <label>{name}</label>
      <button
        className={`toggle-switch ${value ? 'on' : 'off'}`}
        onClick={() => onChange(!value)}
        type="button"
      >
        {value ? 'ON' : 'OFF'}
      </button>
    </div>
  );
}
