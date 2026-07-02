import { createRef, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import AIModelPanel from "../components/AIModelPanel";
import CameraPanel from "../components/CameraPanel";
import {
  DangerZoneIcon,
  FallDetectionIcon,
  FireIcon,
  ForkliftIcon,
  HelmetIcon,
  InactivityDetectionIcon,
  PoseIcon,
  RunningDetectionIcon,
  WorkerGroupIcon,
  WorkZoneIcon,
} from "../components/ModelIcons";
import { getSettings } from "../services/api";

const MAX_STREAM_MODELS = 2;

const MODELS = [
  { key: "pose_anchor",        label: "Pose Detection",               icon: <PoseIcon />,              iconColor: "#0891b2", iconBg: "#e0f7fa", primary: false },
  { key: "ppe",                label: "PPE Detection",                icon: <HelmetIcon />,            iconColor: "#2563eb", iconBg: "#e7efff", primary: true },
  { key: "work_situation",     label: "Work Situation",               icon: <WorkerGroupIcon />,       iconColor: "#7c3aed", iconBg: "#f1e8ff", primary: true },
  { key: "smoke_fire",         label: "Smoke & Fire",                 icon: <FireIcon />,              iconColor: "#ea580c", iconBg: "#fff1e7", primary: true },
  { key: "worker_forklift",    label: "Worker-Forklift",              icon: <ForkliftIcon />,          iconColor: "#15803d", iconBg: "#e9f8ee", primary: true },
  { key: "danger_zone",        label: "Danger Zone",                  icon: <DangerZoneIcon />,        iconColor: "#dc2626", iconBg: "#ffe9e9", primary: true },
  { key: "work_zone",          label: "Work Zone",                    icon: <WorkZoneIcon />,          iconColor: "#16a34a", iconBg: "#e8f9ee", primary: true },
  { key: "fall_detection",     label: "Fall Detection",               icon: <FallDetectionIcon />,     iconColor: "#dc2626", iconBg: "#ffe9e9", primary: false },
  { key: "running_detection",  label: "Unsafe Running",               icon: <RunningDetectionIcon />,  iconColor: "#b45309", iconBg: "#fef3c7", primary: false },
  { key: "inactivity_detection", label: "Inactivity",                icon: <InactivityDetectionIcon />, iconColor: "#6d28d9", iconBg: "#ede9fe", primary: false },
];

const MODEL_LABELS = Object.fromEntries(MODELS.map((m) => [m.key, m.label]));
const SEVERITY_COLORS = { danger: "#dc2626", warning: "#f59e0b", info: "#2563eb" };

function MiniDetectionResults({ events, totalCount, onViewAll }) {
  const recent = events.slice(0, 8);
  return (
    <section className="card mini-results-card">
      <div className="mini-results-header">
        <div className="card-title" style={{ marginBottom: 0 }}>
          Recent Detections
          <span className="mini-results-count">{totalCount}</span>
        </div>
        <button type="button" className="view-all-btn" onClick={onViewAll}>View All →</button>
      </div>
      <div className="mini-events-list">
        {recent.length ? recent.map((event) => (
          <div key={`${event.slot}-${event.id}`} className="mini-event-row">
            <span className="severity-dot" style={{ background: SEVERITY_COLORS[event.severity?.toLowerCase()] || "#94a3b8" }} />
            <span className="mini-event-label">{event.label}</span>
            <span className="mini-event-camera">Camera {event.slot + 1}</span>
            <span className="mini-event-time">{new Date(event.timestamp).toLocaleTimeString()}</span>
          </div>
        )) : (
          <div className="mini-empty">No detections yet.</div>
        )}
      </div>
    </section>
  );
}

function useCameraCount() {
  const [count] = useState(() => {
    const stored = parseInt(localStorage.getItem("safefactory_camera_count") || "1", 10);
    return Math.max(1, Math.min(4, stored));
  });
  return count;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const cameraCount = useCameraCount();

  const [enabledModels, setEnabledModels] = useState(["pose_anchor", "ppe"]);
  const [inferenceStatus, setInferenceStatus] = useState("idle"); // "idle" | "running" | "stopping"
  const [runningModels, setRunningModels] = useState([]);         // actual models backend confirmed
  const [cudaEnabled, setCudaEnabled] = useState(null);
  const [globalLoading, setGlobalLoading] = useState(false);

  const panelRefs = useRef([]);
  panelRefs.current = useMemo(
    () => Array.from({ length: cameraCount }, (_, i) => panelRefs.current[i] ?? createRef()),
    [cameraCount],
  );

  // Per-camera event feed: { [slot]: { events: [...], total: number } }
  const [eventsBySlot, setEventsBySlot] = useState({});

  const [toast, setToast] = useState(null);
  const toastTimer = useRef(null);

  // Load CUDA info once
  useEffect(() => {
    getSettings()
      .then((d) => setCudaEnabled(d.runtime?.gpu_enabled ?? false))
      .catch(() => setCudaEnabled(false));
  }, []);

  const showToast = (text, type) => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    const resolved = type ?? (/fail|error/i.test(text) ? "error" : "success");
    setToast({ text, type: resolved, id: Date.now() });
    toastTimer.current = setTimeout(() => setToast(null), resolved === "error" ? 5000 : 3000);
  };

  const selectedPrimaryCount = enabledModels.filter((k) => MODELS.find((m) => m.key === k)?.primary).length;

  const toggleModel = (modelKey) => {
    if (inferenceStatus === "running") {
      showToast("Stop inference before changing models.", "warning");
      return;
    }
    setEnabledModels((current) => {
      const model = MODELS.find((m) => m.key === modelKey);
      if (current.includes(modelKey)) return current.filter((k) => k !== modelKey);
      if (model?.primary && selectedPrimaryCount >= MAX_STREAM_MODELS) return current;
      return [...current, modelKey];
    });
  };

  const isModelDisabled = (modelKey) => {
    if (inferenceStatus === "running") return true;
    const model = MODELS.find((m) => m.key === modelKey);
    if (!model?.primary || enabledModels.includes(modelKey)) return false;
    return selectedPrimaryCount >= MAX_STREAM_MODELS;
  };

  const handleStart = async () => {
    if (enabledModels.length === 0) {
      showToast("Select at least one AI model.", "warning");
      return;
    }
    setGlobalLoading(true);
    let confirmedModels = null;
    let started = 0;

    for (let i = 0; i < cameraCount; i++) {
      const panel = panelRefs.current[i]?.current;
      if (!panel) continue;
      const models = await panel.start();
      if (models) {
        started++;
        if (!confirmedModels) confirmedModels = models;
      }
    }

    if (started > 0) {
      setRunningModels(confirmedModels || enabledModels);
      setInferenceStatus("running");
      showToast(`${started}/${cameraCount} camera${started > 1 ? "s" : ""} started.`, "success");
    } else {
      showToast("Failed to start inference. Cameras may not be connected yet.", "error");
    }
    setGlobalLoading(false);
  };

  const handleStop = async () => {
    setGlobalLoading(true);
    setInferenceStatus("stopping");
    for (let i = 0; i < cameraCount; i++) {
      const panel = panelRefs.current[i]?.current;
      if (panel?.isActive()) await panel.stop();
    }
    setRunningModels([]);
    setInferenceStatus("idle");
    showToast("Inference stopped.", "success");
    setGlobalLoading(false);
  };

  const slots = useMemo(() => Array.from({ length: cameraCount }, (_, i) => i), [cameraCount]);
  const gridClass = `cameras-grid cameras-grid-${cameraCount}`;

  // Merge every camera's recent events into one feed, newest first, tagged with its source camera
  const { mergedEvents, totalEventCount } = useMemo(() => {
    const merged = [];
    let total = 0;
    slots.forEach((slot) => {
      const bucket = eventsBySlot[slot];
      if (!bucket) return;
      total += bucket.total || 0;
      (bucket.events || []).forEach((event) => merged.push({ ...event, slot }));
    });
    merged.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    return { mergedEvents: merged, totalEventCount: total };
  }, [eventsBySlot, slots]);

  return (
    <div className="dashboard-page">
      <header className="page-header">
        <h1>SafeFactory AI</h1>
        <p>Select AI models, then press Start to begin inference.</p>
      </header>

      {toast && (
        <div key={toast.id} className={`toast toast-${toast.type}`}>
          {toast.text}
        </div>
      )}

      <div className="dashboard-grid">
        {/* Left: AI Models + Inference Controls */}
        <div className="left-column">
          <AIModelPanel
            models={MODELS}
            enabledModels={enabledModels}
            onToggle={toggleModel}
            isDisabled={isModelDisabled}
          />

          {/* Inference controls card */}
          <section className="card inference-ctrl-card">
            {/* Status row */}
            <div className="inference-status-row">
              <span className={`cuda-badge ${cudaEnabled ? "cuda-on" : cudaEnabled === false ? "cuda-off" : "cuda-loading"}`}>
                {cudaEnabled === null ? "…" : cudaEnabled ? "CUDA" : "CPU"}
              </span>
              <span className={`infer-status-badge ${inferenceStatus}`}>
                {inferenceStatus === "running" ? "● Running" : inferenceStatus === "stopping" ? "◌ Stopping" : "○ Idle"}
              </span>
              <span className="camera-count-badge">
                {cameraCount} cam{cameraCount > 1 ? "s" : ""}
              </span>
            </div>

            {/* Running models (shown only when running) */}
            {inferenceStatus === "running" && runningModels.length > 0 && (
              <div className="running-models-row">
                <span className="running-models-label">Active:</span>
                {runningModels.map((k) => (
                  <span key={k} className="running-model-chip">
                    {MODEL_LABELS[k] || k}
                  </span>
                ))}
              </div>
            )}

            {/* Selected models (shown when idle) */}
            {inferenceStatus === "idle" && enabledModels.length > 0 && (
              <div className="running-models-row">
                <span className="running-models-label">Selected:</span>
                {enabledModels.map((k) => (
                  <span key={k} className="selected-model-chip">
                    {MODEL_LABELS[k] || k}
                  </span>
                ))}
              </div>
            )}

            {/* Start / Stop buttons */}
            <div className="inference-btn-row">
              <button
                type="button"
                className="button infer-start-btn"
                onClick={handleStart}
                disabled={globalLoading || inferenceStatus === "running" || enabledModels.length === 0}
              >
                ▶ Start
              </button>
              <button
                type="button"
                className="button button-secondary infer-stop-btn"
                onClick={handleStop}
                disabled={globalLoading || inferenceStatus !== "running"}
              >
                ■ Stop
              </button>
            </div>
          </section>
        </div>

        {/* Center: Camera grid */}
        <div className="cameras-container">
          <div className={gridClass}>
            {slots.map((slot, idx) => (
              <CameraPanel
                key={slot}
                ref={panelRefs.current[idx]}
                slot={slot}
                autoConnect
                enabledModels={enabledModels}
                onEventsUpdate={(evts, total) =>
                  setEventsBySlot((prev) => ({ ...prev, [slot]: { events: evts, total } }))
                }
                onShowToast={showToast}
              />
            ))}
          </div>
        </div>

        {/* Right: Mini Results */}
        <div className="right-column">
          <MiniDetectionResults
            events={mergedEvents}
            totalCount={totalEventCount}
            onViewAll={() => navigate("/detections")}
          />
        </div>
      </div>
    </div>
  );
}
