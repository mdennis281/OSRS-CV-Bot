import type { ConfigWidgetProps, FloatValue } from '../../types/config';

export default function FloatInput({ name, value, onChange }: ConfigWidgetProps<FloatValue>) {
  return (
    <div className="config-widget float-input">
      <label>{name}</label>
      <input
        type="number"
        step={0.1}
        value={value ?? 0}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      />
    </div>
  );
}
