import type { ConfigWidgetProps, RGBListValue, RGBValue } from '../../types/config';
import RGBInput from './RGBInput';

export default function RGBListInput({ name, value, onChange }: ConfigWidgetProps<RGBListValue>) {
  const items = value ?? [];

  const updateColor = (index: number, rgb: RGBValue) => {
    const next = items.map((entry, i) =>
      i === index ? { type: 'RGB' as const, value: rgb } : entry,
    );
    onChange(next);
  };

  const addColor = () => {
    onChange([...items, { type: 'RGB', value: { rgb: [255, 0, 0], hex: '#FF0000' } }]);
  };

  const removeColor = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  return (
    <div className="config-widget rgb-list-input">
      <label>{name}</label>
      {items.map((entry, i) => (
        <div key={i} className="rgb-list-row">
          <RGBInput
            name={`${name}[${i}]`}
            value={entry.value}
            onChange={(v) => updateColor(i, v)}
          />
          <button className="remove-btn" onClick={() => removeColor(i)}>✕</button>
        </div>
      ))}
      <button className="add-btn" onClick={addColor}>+ Add Color</button>
    </div>
  );
}
