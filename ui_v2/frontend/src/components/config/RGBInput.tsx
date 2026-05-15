import type { ConfigWidgetProps, RGBValue } from '../../types/config';

function rgbToHex(r: number, g: number, b: number) {
  return '#' + [r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('');
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

export default function RGBInput({ name, value, onChange }: ConfigWidgetProps<RGBValue>) {
  const [r, g, b] = value?.rgb ?? [0, 0, 0];
  const hex = value?.hex ?? rgbToHex(r, g, b);

  const update = (rgb: [number, number, number]) => {
    onChange({ rgb, hex: rgbToHex(...rgb) });
  };

  return (
    <div className="config-widget rgb-input">
      <label>{name}</label>
      <div className="rgb-fields">
        <input type="number" min={0} max={255} value={r}
          onChange={(e) => update([+e.target.value, g, b])} />
        <input type="number" min={0} max={255} value={g}
          onChange={(e) => update([r, +e.target.value, b])} />
        <input type="number" min={0} max={255} value={b}
          onChange={(e) => update([r, g, +e.target.value])} />
        <input type="color" value={hex}
          onChange={(e) => {
            const rgb = hexToRgb(e.target.value);
            onChange({ rgb, hex: e.target.value });
          }} />
        <span className="color-swatch" style={{ background: hex }} />
      </div>
    </div>
  );
}
