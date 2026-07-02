import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";

import {
  clearZones,
  connectDemo,
  connectSource,
  getFrameUrl,
  getResults,
  getZones,
  pauseInference,
  resumeInference,
  saveSnapshot,
  saveZone,
  startInference,
  stopInference,
} from "../services/api";
import LivePreview from "./LivePreview";

const RESULTS_PAGE_SIZE = 10;

function readSlotConfig(slot) {
  try {
    const configs = JSON.parse(localStorage.getItem("safefactory_slot_sources") || "{}");
    return configs[String(slot)] || { type: "demo", index: slot };
  } catch {
    return { type: "demo", index: slot };
  }
}

const CameraPanel = forwardRef(function CameraPanel(
  {
    slot,
    autoConnect = false,
    enabledModels,
    onEventsUpdate,
    onShowToast,
  },
  ref,
) {
  const [sourceType, setSourceType] = useState(() => {
    if (autoConnect) return "video";
    try {
      const saved = JSON.parse(localStorage.getItem("safefactory_rtsp_urls") || "{}");
      return saved[String(slot)] ? "rtsp" : "video";
    } catch { return "video"; }
  });
  const [rtspUrl, setRtspUrl] = useState(() => {
    if (autoConnect) return "";
    try {
      const saved = JSON.parse(localStorage.getItem("safefactory_rtsp_urls") || "{}");
      return saved[String(slot)] || "";
    } catch { return ""; }
  });
  const [file, setFile] = useState(null);
  const [connectedSource, setConnectedSource] = useState(null);
  const [sessionStatus, setSessionStatus] = useState("idle");
  const [previewVersion, setPreviewVersion] = useState(Date.now());
  const [sourceOpen, setSourceOpen] = useState(!autoConnect);
  const fileInputRef = useRef(null);

  // Zone drawing — fully self-contained per camera
  const [isDrawingZone, setIsDrawingZone] = useState(false);
  const [zoneType, setZoneType] = useState("danger_zone");
  const [savedZones, setSavedZones] = useState([]);
  const [currentPolygon, setCurrentPolygon] = useState([]);
  const [polygonClosed, setPolygonClosed] = useState(false);
  const [workerCount, setWorkerCount] = useState(0);

  const isInferenceActive = ["running", "paused"].includes(sessionStatus);

  const stateRef = useRef(null);
  stateRef.current = {
    sourceType, rtspUrl, file, connectedSource, enabledModels, slot,
    isInferenceActive, sessionStatus, onShowToast,
  };

  // Auto-connect on mount: show preview only — NO auto-start of inference
  useEffect(() => {
    if (!autoConnect) return;
    let cancelled = false;

    const init = async () => {
      // Restore already-running session (e.g. after page navigation)
      try {
        const result = await getResults(1, RESULTS_PAGE_SIZE, slot);
        if (cancelled) return;
        if (["running", "paused", "connected"].includes(result.status) && result.source) {
          setConnectedSource(result.source);
          setSessionStatus(result.status);
          setPreviewVersion(Date.now());
          if (result.source?.id) {
            try { setSavedZones(await getZones(result.source.id)); } catch (_) {}
          }
          return;
        }
      } catch (_) {}

      if (cancelled) return;

      // Connect fresh from slot config (no inference start)
      const config = readSlotConfig(slot);
      try {
        let response;
        if (config.type === "rtsp" && config.url) {
          const formData = new FormData();
          formData.append("source_type", "rtsp");
          formData.append("rtsp_url", config.url);
          response = await connectSource(formData, slot);
        } else {
          response = await connectDemo(config.index ?? slot, slot);
        }
        if (cancelled) return;

        const src = response.source;
        setConnectedSource(src);
        setSessionStatus(response.status);
        setPreviewVersion(Date.now());
        if (src?.id) {
          try { setSavedZones(await getZones(src.id)); } catch (_) {}
        }
      } catch (err) {
        console.error(`[CameraPanel slot=${slot}] auto-connect failed:`, err?.response?.data || err);
      }
    };

    init();
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Stop inference when component unmounts (camera count decreased)
  useEffect(() => {
    return () => {
      if (stateRef.current?.isInferenceActive) {
        stopInference(stateRef.current.slot).catch(() => {});
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!autoConnect) {
      if (isInferenceActive) setSourceOpen(false);
      else if (!connectedSource) setSourceOpen(true);
    }
  }, [autoConnect, isInferenceActive, connectedSource]);

  const previewUrl = useMemo(() => {
    if (!connectedSource) return "";
    return getFrameUrl(previewVersion, slot, connectedSource?.id);
  }, [connectedSource, previewVersion, slot]);

  useEffect(() => {
    if (!["running", "paused", "completed", "connected"].includes(sessionStatus)) return undefined;
    const isRunning = sessionStatus === "running";
    const id = window.setInterval(async () => {
      try {
        const result = await getResults(1, RESULTS_PAGE_SIZE, slot);
        setSessionStatus(result.status || "idle");
        onEventsUpdate?.(result.events || [], result.pagination?.total_events ?? 0);
        setWorkerCount(result.worker_count || 0);
        setPreviewVersion(Date.now());
      } catch (_) {}
    }, isRunning ? 300 : 1000);
    return () => window.clearInterval(id);
  }, [sessionStatus, slot]);

  const _connect = useCallback(async () => {
    const { sourceType, rtspUrl, file, slot, onShowToast } = stateRef.current;
    if (sourceType === "rtsp" && !rtspUrl.trim()) {
      onShowToast?.(`Camera ${slot + 1}: enter an RTSP URL.`, "warning");
      return false;
    }
    if (sourceType !== "rtsp" && !file) {
      onShowToast?.(`Camera ${slot + 1}: choose a ${sourceType} file.`, "warning");
      return false;
    }
    try {
      const formData = new FormData();
      formData.append("source_type", sourceType);
      if (sourceType === "rtsp") formData.append("rtsp_url", rtspUrl);
      else formData.append("file", file);
      const response = await connectSource(formData, slot);
      const src = response.source;
      setConnectedSource(src);
      setSessionStatus(response.status);
      setPreviewVersion(Date.now());
      if (src?.id) {
        try { setSavedZones(await getZones(src.id)); } catch (_) {}
      }
      return true;
    } catch (err) {
      stateRef.current.onShowToast?.(
        err.response?.data?.detail || `Camera ${slot + 1}: failed to connect.`,
        "error",
      );
      return false;
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Returns the actual enabled_models list from backend (or null on failure)
  const _start = useCallback(async () => {
    const { connectedSource, enabledModels, slot, onShowToast } = stateRef.current;
    if (!connectedSource) return null;
    try {
      const response = await startInference(
        { source_id: connectedSource.id, enabled_models: enabledModels },
        slot,
      );
      setSessionStatus(response.status);
      setPreviewVersion(Date.now());
      return response.enabled_models || enabledModels;
    } catch (err) {
      onShowToast?.(err.response?.data?.detail || `Camera ${slot + 1}: failed to start.`, "error");
      return null;
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const _stop = useCallback(async () => {
    const { slot } = stateRef.current;
    try {
      const r = await stopInference(slot);
      setSessionStatus(r.status);
      setPreviewVersion(Date.now());
      return true;
    } catch (_) { return false; }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useImperativeHandle(ref, () => ({
    connect: _connect,
    start: _start,
    stop: _stop,
    isConnected: () => Boolean(stateRef.current.connectedSource),
    isActive: () => stateRef.current.isInferenceActive,
  }), [_connect, _start, _stop]);

  const handlePauseResume = async () => {
    try {
      const r = sessionStatus === "paused"
        ? await resumeInference(slot)
        : await pauseInference(slot);
      setSessionStatus(r.status);
    } catch (_) {}
  };

  const handleSnapshot = async () => {
    try {
      await saveSnapshot(slot);
      onShowToast?.("Snapshot saved.", "success");
    } catch (_) {}
  };

  const handleToggleDrawZone = () => {
    setIsDrawingZone((prev) => {
      const next = !prev;
      if (next) {
        setCurrentPolygon([]);
        setPolygonClosed(false);
      }
      return next;
    });
  };

  const handleSetZoneType = (type) => {
    setZoneType(type);
    setCurrentPolygon([]);
    setPolygonClosed(false);
  };

  const handleAddPoint = (point) => setCurrentPolygon((prev) => [...prev, point]);

  const handleFinishPolygon = () => {
    if (currentPolygon.length >= 3) setPolygonClosed(true);
  };

  const handleClearZone = async () => {
    setCurrentPolygon([]);
    setPolygonClosed(false);
    if (!connectedSource) return;
    const hasSavedOfType = savedZones.some((zone) => zone.zone_type === zoneType);
    if (!hasSavedOfType) return;
    try {
      await clearZones(connectedSource.id, zoneType);
      setSavedZones(await getZones(connectedSource.id));
      const label = zoneType === "danger_zone" ? "danger" : "work";
      onShowToast?.(`Camera ${slot + 1}: ${label} zones cleared.`, "success");
    } catch (error) {
      onShowToast?.(error.response?.data?.detail || `Camera ${slot + 1}: failed to clear zones.`, "error");
    }
  };

  const handleSaveZoneClick = async () => {
    if (!connectedSource || currentPolygon.length < 3) return;
    try {
      await saveZone({ source_id: connectedSource.id, zone_type: zoneType, points: currentPolygon });
      setSavedZones(await getZones(connectedSource.id));
      setCurrentPolygon([]);
      setPolygonClosed(false);
      onShowToast?.(`Camera ${slot + 1}: zone saved.`, "success");
    } catch (error) {
      onShowToast?.(error.response?.data?.detail || `Camera ${slot + 1}: failed to save zone.`, "error");
    }
  };

  const zoneEditor = (
    <div className="camera-zone-block">
      <button
        type="button"
        className={`camera-zone-toggle-btn${isDrawingZone ? " active" : ""}`}
        onClick={handleToggleDrawZone}
        disabled={!connectedSource}
      >
        {isDrawingZone ? "✕ Cancel" : "▦ Draw Zone"}
      </button>

      {isDrawingZone && (
        <>
          <button
            type="button"
            className={`camera-zone-type-tab danger${zoneType === "danger_zone" ? " active" : ""}`}
            onClick={() => handleSetZoneType("danger_zone")}
          >
            Danger
          </button>
          <button
            type="button"
            className={`camera-zone-type-tab work${zoneType === "work_zone" ? " active" : ""}`}
            onClick={() => handleSetZoneType("work_zone")}
          >
            Work
          </button>
          <button type="button" className="camera-zone-mini-btn" onClick={handleClearZone}>
            Clear
          </button>
          <button
            type="button"
            className="camera-zone-mini-btn primary"
            onClick={handleSaveZoneClick}
            disabled={currentPolygon.length < 3}
          >
            Save ({currentPolygon.length})
          </button>
          {workerCount > 0 && <span className="camera-zone-worker-chip">{workerCount} in zone</span>}
        </>
      )}
    </div>
  );

  if (autoConnect) {
    return (
      <div className="camera-panel camera-panel-auto card">
        <div className="camera-panel-header">
          <div className="camera-slot-info">
            <span className="camera-slot-label">Camera {slot + 1}</span>
            {connectedSource?.name && (
              <span className="camera-source-name" title={connectedSource.name}>
                {connectedSource.name.length > 22
                  ? `${connectedSource.name.slice(0, 20)}…`
                  : connectedSource.name}
              </span>
            )}
          </div>
          <span className={`live-indicator ${sessionStatus === "running" ? "on" : ""}`}>
            {sessionStatus === "running" ? "Live" : sessionStatus || "idle"}
          </span>
        </div>
        <div className="camera-preview-wrap">
          <LivePreview
            previewUrl={previewUrl}
            savedZones={savedZones}
            currentPolygon={currentPolygon}
            activeZoneType={zoneType}
            onAddPoint={handleAddPoint}
            onFinishPolygon={handleFinishPolygon}
            onPauseResume={handlePauseResume}
            onStop={_stop}
            onSnapshot={handleSnapshot}
            sessionStatus={sessionStatus}
            canDraw={isDrawingZone && Boolean(connectedSource)}
            workerCount={workerCount}
            polygonClosed={polygonClosed}
            compact
          />
        </div>
        {zoneEditor}
      </div>
    );
  }

  return (
    <div className="camera-panel card">
      <div className="camera-panel-header">
        <div className="camera-slot-info">
          <span className="camera-slot-label">Camera {slot + 1}</span>
          {connectedSource?.name && (
            <span className="camera-source-name" title={connectedSource.name}>
              {connectedSource.name.length > 20
                ? `${connectedSource.name.slice(0, 18)}…`
                : connectedSource.name}
            </span>
          )}
        </div>
        <div className="camera-header-right">
          <span className={`live-indicator ${sessionStatus === "running" ? "on" : ""}`}>
            {sessionStatus || "idle"}
          </span>
          <button
            type="button"
            className="camera-toggle-btn"
            title={sourceOpen ? "Hide source input" : "Show source input"}
            onClick={() => setSourceOpen((v) => !v)}
          >
            {sourceOpen ? "▲" : "▼"}
          </button>
        </div>
      </div>

      {sourceOpen && (
        <div className="camera-source-block">
          <div className="camera-type-tabs">
            {["rtsp", "video", "image"].map((t) => (
              <button
                key={t}
                type="button"
                className={`camera-type-tab${sourceType === t ? " active" : ""}`}
                onClick={() => { setSourceType(t); setFile(null); }}
                disabled={isInferenceActive}
              >
                {t.toUpperCase()}
              </button>
            ))}
          </div>
          {sourceType === "rtsp" ? (
            <input
              className="camera-url-input"
              placeholder="rtsp://..."
              value={rtspUrl}
              onChange={(e) => setRtspUrl(e.target.value)}
              disabled={isInferenceActive}
            />
          ) : (
            <button
              type="button"
              className="camera-file-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={isInferenceActive}
            >
              {file ? file.name : `Choose ${sourceType}…`}
            </button>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept={sourceType === "image" ? "image/*" : "video/*"}
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            hidden
          />
        </div>
      )}

      <div className="camera-preview-wrap">
        <LivePreview
          previewUrl={previewUrl}
          savedZones={savedZones}
          currentPolygon={currentPolygon}
          activeZoneType={zoneType}
          onAddPoint={handleAddPoint}
          onFinishPolygon={handleFinishPolygon}
          onPauseResume={handlePauseResume}
          onStop={_stop}
          onSnapshot={handleSnapshot}
          sessionStatus={sessionStatus}
          canDraw={isDrawingZone && Boolean(connectedSource)}
          workerCount={workerCount}
          polygonClosed={polygonClosed}
        />
      </div>
      {zoneEditor}
    </div>
  );
});

export default CameraPanel;
