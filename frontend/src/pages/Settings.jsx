import { useEffect, useState } from "react";

import { getSettings } from "../services/api";

function useCameraCount() {
  const [count, setCount] = useState(() => {
    const stored = parseInt(localStorage.getItem("safefactory_camera_count") || "1", 10);
    return Math.max(1, Math.min(4, stored));
  });
  const update = (n) => {
    localStorage.setItem("safefactory_camera_count", String(n));
    setCount(n);
  };
  return [count, update];
}

function useSlotSources() {
  const defaultConfig = (slot) => ({ type: "demo", index: slot });

  const [configs, setConfigs] = useState(() => {
    try { return JSON.parse(localStorage.getItem("safefactory_slot_sources") || "{}"); }
    catch { return {}; }
  });

  const getConfig = (slot) => configs[String(slot)] || defaultConfig(slot);

  const updateConfig = (slot, patch) => {
    setConfigs((prev) => {
      const current = prev[String(slot)] || defaultConfig(slot);
      const next = { ...prev, [String(slot)]: { ...current, ...patch } };
      localStorage.setItem("safefactory_slot_sources", JSON.stringify(next));
      return next;
    });
  };

  return { getConfig, updateConfig };
}

function SlotSourceRow({ slot, getConfig, updateConfig }) {
  const cfg = getConfig(slot);

  return (
    <div className="slot-source-row">
      <div className="slot-source-header">
        <span className="slot-source-label">Camera {slot + 1}</span>
        <div className="slot-type-tabs">
          <button
            type="button"
            className={`slot-type-tab${cfg.type === "demo" ? " active" : ""}`}
            onClick={() => updateConfig(slot, { type: "demo", index: slot })}
          >
            Demo
          </button>
          <button
            type="button"
            className={`slot-type-tab${cfg.type === "rtsp" ? " active" : ""}`}
            onClick={() => updateConfig(slot, { type: "rtsp", url: cfg.url || "" })}
          >
            RTSP
          </button>
        </div>
      </div>

      {cfg.type === "demo" ? (
        <div className="slot-demo-info">
          <span>Demo video {(cfg.index ?? slot) + 1}</span>
          <select
            className="slot-demo-select"
            value={cfg.index ?? slot}
            onChange={(e) => updateConfig(slot, { index: Number(e.target.value) })}
          >
            {[0, 1, 2, 3].map((i) => (
              <option key={i} value={i}>Video {i + 1}</option>
            ))}
          </select>
        </div>
      ) : (
        <input
          className="rtsp-url-input"
          type="text"
          placeholder="rtsp://user:pass@192.168.1.x:554/stream"
          value={cfg.url || ""}
          onChange={(e) => updateConfig(slot, { url: e.target.value })}
        />
      )}
    </div>
  );
}

export default function Settings() {
  const [settingsData, setSettingsData] = useState(null);
  const [error, setError] = useState("");
  const [cameraCount, setCameraCount] = useCameraCount();
  const { getConfig, updateConfig } = useSlotSources();

  useEffect(() => {
    getSettings()
      .then(setSettingsData)
      .catch((err) => setError(err.response?.data?.detail || "Failed to load settings."));
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Settings</h1>
        <p>Camera sources, layout, and runtime inference configuration.</p>
      </header>

      {error ? <div className="message-banner">{error}</div> : null}

      <div className="settings-grid">
        {/* Camera layout */}
        <section className="card">
          <div className="card-title">Camera Layout</div>
          <p className="helper-text" style={{ marginTop: 0, marginBottom: 16 }}>
            Number of camera slots shown on the Dashboard.
          </p>
          <div className="camera-count-selector">
            {[1, 2, 3, 4].map((n) => (
              <button
                key={n}
                type="button"
                className={`camera-count-btn${cameraCount === n ? " active" : ""}`}
                onClick={() => setCameraCount(n)}
              >
                <span className="camera-count-num">{n}</span>
                <span className="camera-count-label">
                  {n === 1 ? "Single" : n === 2 ? "Dual" : n === 3 ? "Triple" : "Quad"}
                </span>
                <div className="camera-count-preview">
                  {Array.from({ length: n }, (_, i) => (
                    <div key={i} className="camera-count-cell" />
                  ))}
                </div>
              </button>
            ))}
          </div>
          <p className="helper-text" style={{ marginTop: 12 }}>
            Current: <strong>{cameraCount} camera{cameraCount > 1 ? "s" : ""}</strong>
          </p>
        </section>

        {/* Per-slot source configuration */}
        <section className="card">
          <div className="card-title">Camera Sources</div>
          <p className="helper-text" style={{ marginTop: 0, marginBottom: 16 }}>
            Each camera slot can use a built-in demo video or a live RTSP stream.
            Changes apply on next Dashboard load.
          </p>
          <div className="slot-sources-list">
            {[0, 1, 2, 3].map((slot) => (
              <SlotSourceRow
                key={slot}
                slot={slot}
                getConfig={getConfig}
                updateConfig={updateConfig}
              />
            ))}
          </div>
        </section>

        {settingsData ? (
          <>
            <section className="card">
              <div className="card-title">Model Paths</div>
              <div className="settings-list">
                {Object.entries(settingsData.model_paths).map(([key, path]) => (
                  <div key={key} className="settings-row">
                    <span>{key}</span>
                    <code>{path}</code>
                  </div>
                ))}
              </div>
            </section>

            <section className="card">
              <div className="card-title">Thresholds</div>
              <div className="settings-list">
                <div className="settings-row">
                  <span>Default Confidence</span>
                  <strong>{settingsData.default_confidence}</strong>
                </div>
                <div className="settings-row">
                  <span>Forklift Warning Distance</span>
                  <strong>{settingsData.forklift_warning_distance}px</strong>
                </div>
                <div className="settings-row">
                  <span>Forklift Danger Distance</span>
                  <strong>{settingsData.forklift_danger_distance}px</strong>
                </div>
                <div className="settings-row">
                  <span>Result History Limit</span>
                  <strong>{settingsData.result_history_limit}</strong>
                </div>
                <div className="settings-row">
                  <span>Results Per Page</span>
                  <strong>{settingsData.results_page_size}</strong>
                </div>
                <div className="settings-row">
                  <span>Max Stream Models</span>
                  <strong>{settingsData.max_stream_models}</strong>
                </div>
                <div className="settings-row">
                  <span>Max Camera Slots</span>
                  <strong>{settingsData.max_camera_slots}</strong>
                </div>
              </div>
            </section>

            <section className="card">
              <div className="card-title">Zone Dependencies</div>
              <div className="settings-list">
                {Object.entries(settingsData.zone_dependencies).map(([key, values]) => (
                  <div key={key} className="settings-row">
                    <span>{key}</span>
                    <strong>{values.join(", ")}</strong>
                  </div>
                ))}
              </div>
            </section>

            <section className="card">
              <div className="card-title">Runtime</div>
              <div className="settings-list">
                <div className="settings-row">
                  <span>Inference Device</span>
                  <strong>{settingsData.runtime.device}</strong>
                </div>
                <div className="settings-row">
                  <span>GPU Enabled</span>
                  <strong>{settingsData.runtime.gpu_enabled ? "Yes" : "No"}</strong>
                </div>
                <div className="settings-row">
                  <span>Half Precision</span>
                  <strong>{settingsData.runtime.half_precision ? "Yes" : "No"}</strong>
                </div>
              </div>
            </section>
          </>
        ) : (
          <section className="card">
            <div className="card-title">Loading</div>
            <p>Fetching runtime settings…</p>
          </section>
        )}
      </div>
    </div>
  );
}
