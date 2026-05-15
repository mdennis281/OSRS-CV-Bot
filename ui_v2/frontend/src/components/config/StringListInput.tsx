import { useState } from 'react';
import type { ConfigWidgetProps, StringListValue } from '../../types/config';

export default function StringListInput({ name, value, onChange }: ConfigWidgetProps<StringListValue>) {
  const items = value ?? [];
  const [draft, setDraft] = useState('');

  const add = () => {
    if (draft.trim()) {
      onChange([...items, draft.trim()]);
      setDraft('');
    }
  };

  const remove = (index: number) => {
    onChange(items.filter((_, i) => i !== index));
  };

  return (
    <div className="config-widget string-list-input">
      <label>{name}</label>
      <div className="tag-list">
        {items.map((s, i) => (
          <span key={i} className="tag removable">
            {s}
            <button onClick={() => remove(i)}>✕</button>
          </span>
        ))}
      </div>
      <div className="tag-add">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add entry..."
          onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), add())}
        />
        <button onClick={add}>+</button>
      </div>
    </div>
  );
}
