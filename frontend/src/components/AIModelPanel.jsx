export default function AIModelPanel({ models, enabledModels, onToggle, isDisabled }) {
  return (
    <section className="card">
      <div className="card-title">AI Models</div>
      <div className="model-list">
        {models.map((model) => (
          <label key={model.key} className={`model-row${isDisabled(model.key) ? " disabled" : ""}`}>
            <div className="model-meta">
              <div className="model-icon">{model.icon}</div>
              <div className="model-label">{model.label}</div>
            </div>
            <button
              type="button"
              className={`toggle${enabledModels.includes(model.key) ? " on" : ""}`}
              onClick={() => onToggle(model.key)}
              disabled={isDisabled(model.key)}
            >
              <span className="toggle-handle" />
            </button>
          </label>
        ))}
      </div>
    </section>
  );
}
