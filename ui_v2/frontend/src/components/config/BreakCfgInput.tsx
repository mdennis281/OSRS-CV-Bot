import type { ConfigWidgetProps, BreakCfgValue, RangeValue } from '../../types/config';

export default function BreakCfgInput({ name, value, onChange }: ConfigWidgetProps<BreakCfgValue>) {
  const dur = value?.break_duration?.value ?? [300, 600];
  const chance = value?.break_chance ?? 0.02;

  const updateDuration = (v: RangeValue) => {
    onChange({
      break_duration: { type: 'Range', value: v },
      break_chance: chance,
    });
  };

  return (
    <div className="config-widget break-cfg-input">
      <label>{name}</label>
      <div className="break-cfg-fields">
        <div className="field-group">
          <span>Min Duration (s)</span>
          <input type="number" value={dur[0]}
            onChange={(e) => updateDuration([+e.target.value, dur[1]])} />
        </div>
        <div className="field-group">
          <span>Max Duration (s)</span>
          <input type="number" value={dur[1]}
            onChange={(e) => updateDuration([dur[0], +e.target.value])} />
        </div>
        <div className="field-group">
          <span>Break Chance</span>
          <input type="number" step="0.001" min={0} max={1} value={chance}
            onChange={(e) => onChange({
              break_duration: { type: 'Range', value: dur },
              break_chance: +e.target.value,
            })} />
        </div>
      </div>
    </div>
  );
}
