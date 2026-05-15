import type { ConfigWidgetProps, StringValue } from '../../types/config';

export default function StringInput({ name, value, onChange }: ConfigWidgetProps<StringValue>) {
  return (
    <div className="config-widget string-input">
      <label>{name}</label>
      <input
        type="text"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
