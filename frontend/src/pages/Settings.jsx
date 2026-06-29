import { useEffect, useState } from "react";

import { getSettings } from "../services/api";

export default function Settings() {
  const [settingsData, setSettingsData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getSettings()
      .then(setSettingsData)
      .catch((err) => setError(err.response?.data?.detail || "Failed to load settings."));
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Settings</h1>
        <p>Runtime model paths and default inference thresholds.</p>
      </header>

      {error ? <div className="message-banner">{error}</div> : null}

      {settingsData ? (
        <div className="settings-grid">
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
        </div>
      ) : (
        <section className="card">
          <div className="card-title">Loading</div>
          <p>Fetching runtime settings…</p>
        </section>
      )}
    </div>
  );
}
