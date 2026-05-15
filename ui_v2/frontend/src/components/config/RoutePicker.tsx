import type { ConfigWidgetProps, RouteValue, WaypointValue } from '../../types/config';

export default function RoutePicker({ name, value, onChange }: ConfigWidgetProps<RouteValue>) {
  const waypoints = value ?? [];

  const updateWp = (index: number, field: keyof WaypointValue, v: number) => {
    const next = waypoints.map((wp, i) =>
      i === index ? { ...wp, value: { ...wp.value, [field]: v } } : wp,
    );
    onChange(next);
  };

  const addWaypoint = () => {
    onChange([
      ...waypoints,
      { type: 'Waypoint', value: { x: 0, y: 0, z: 0, chunk: 0, tolerance: 5 } },
    ]);
  };

  const removeWaypoint = (index: number) => {
    onChange(waypoints.filter((_, i) => i !== index));
  };

  const reverse = () => onChange([...waypoints].reverse());

  return (
    <div className="config-widget route-picker">
      <label>{name}</label>
      {waypoints.length > 0 && (
        <div className="route-row route-header">
          <span className="route-idx"></span>
          <span className="route-col-label">X</span>
          <span className="route-col-label">Y</span>
          <span className="route-col-label">Z</span>
          <span className="route-col-label">Chunk</span>
          <span className="route-col-label">Tol</span>
          <span className="route-remove-spacer"></span>
        </div>
      )}
      <div className="route-list">
        {waypoints.map((wp, i) => (
          <div key={i} className="route-row">
            <span className="route-idx">#{i + 1}</span>
            {(['x', 'y', 'z', 'chunk', 'tolerance'] as const).map((f) => (
              <input
                key={f}
                type="number"
                title={f}
                placeholder={f}
                value={wp.value[f]}
                onChange={(e) => updateWp(i, f, +e.target.value)}
              />
            ))}
            <button className="remove-btn" onClick={() => removeWaypoint(i)}>✕</button>
          </div>
        ))}
      </div>
      <div className="route-actions">
        <button onClick={addWaypoint}>+ Add Waypoint</button>
        <button onClick={reverse} disabled={waypoints.length < 2}>Reverse</button>
      </div>
    </div>
  );
}
