export default function ZoneTools({
  activeZoneType,
  setActiveZoneType,
  currentPolygon,
  onClear,
  onSave,
  workerCount,
  disabled,
}) {
  return (
    <section className="card">
      <div className="card-title">Zone Tools</div>
      <label className="field-label">Zone Type</label>
      <div className="segmented-control">
        <button
          type="button"
          className={`segment danger${activeZoneType === "danger_zone" ? " active" : ""}`}
          onClick={() => setActiveZoneType("danger_zone")}
        >
          Danger Zone
        </button>
        <button
          type="button"
          className={`segment work${activeZoneType === "work_zone" ? " active" : ""}`}
          onClick={() => setActiveZoneType("work_zone")}
        >
          Work Zone
        </button>
      </div>

      <p className="helper-text">
        Draw a polygon on the preview to define the zone. Double-click to finish. Current points: {currentPolygon.length}
      </p>

      <div className="button-row">
        <button type="button" className="button button-secondary" onClick={onClear} disabled={disabled}>
          Clear Zone
        </button>
        <button
          type="button"
          className="button"
          onClick={onSave}
          disabled={disabled || currentPolygon.length < 3}
        >
          Save Zone
        </button>
      </div>

      <div className="zone-counter">
        <span>Workers in Work Zone</span>
        <strong>{workerCount}</strong>
      </div>
    </section>
  );
}
