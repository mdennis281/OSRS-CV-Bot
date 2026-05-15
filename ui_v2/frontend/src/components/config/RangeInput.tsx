import type { ConfigWidgetProps, RangeValue } from '../../types/config';

export default function RangeInput({ name, value, onChange }: ConfigWidgetProps<RangeValue>) {
  const [min, max] = value ?? [0, 0];

  return (
    <div className="config-widget range-input">
      <label>{name}</label>
      <div className="range-fields">
        <input type="number" step="any" value={min}
          onChange={(e) => onChange([+e.target.value, max])} placeholder="Min" />
        <span>–</span>
        <input type="number" step="any" value={max}
          onChange={(e) => onChange([min, +e.target.value])} placeholder="Max" />
      </div>
    </div>
  );
}
