import type { ConfigWidgetProps, IntValue } from '../../types/config';

export default function IntInput({ name, value, onChange }: ConfigWidgetProps<IntValue>) {
  return (
    <div className="config-widget int-input">
      <label>{name}</label>
      <input
        type="number"
        step={1}
        value={value ?? 0}
        onChange={(e) => onChange(parseInt(e.target.value, 10) || 0)}
      />
    </div>
  );
}
