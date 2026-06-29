import { useEffect, useMemo, useState } from "react";

import AIModelPanel from "../components/AIModelPanel";
import DetectionResults from "../components/DetectionResults";
import InputSourceCard from "../components/InputSourceCard";
import LivePreview from "../components/LivePreview";
import ZoneTools from "../components/ZoneTools";
import {
  connectSource,
  getFrameUrl,
  getResults,
  getStreamUrl,
  getZones,
  pauseInference,
  resumeInference,
  saveSnapshot,
  saveZone,
  startInference,
  stopInference,
} from "../services/api";

const MAX_STREAM_MODELS = 2;
const RESULTS_PAGE_SIZE = 10;

const MODELS = [
  { key: "ppe", label: "PPE Detection", icon: "PPE", primary: true },
  { key: "work_situation", label: "Work Situation Classification", icon: "WS", primary: true },
  { key: "smoke_fire", label: "Smoke & Fire Detection", icon: "SF", primary: true },
  { key: "worker_forklift", label: "Worker-Forklift Detection", icon: "FW", primary: true },
  { key: "danger_zone", label: "Danger Zone Detection", icon: "DZ", primary: true },
  { key: "work_zone", label: "Work Zone Detection", icon: "WZ", primary: true },
];

const EMPTY_PAGINATION = { page: 1, page_size: RESULTS_PAGE_SIZE, total_events: 0, total_pages: 1 };
const VISIBLE_MODEL_KEYS = new Set(MODELS.map((model) => model.key));

export default function Dashboard() {
  const [sourceType, setSourceType] = useState("rtsp");
  const [rtspUrl, setRtspUrl] = useState("");
  const [file, setFile] = useState(null);
  const [connectedSource, setConnectedSource] = useState(null);
  const [enabledModels, setEnabledModels] = useState(["ppe"]);
  const [sessionStatus, setSessionStatus] = useState("idle");
  const [savedZones, setSavedZones] = useState([]);
  const [activeZoneType, setActiveZoneType] = useState("danger_zone");
  const [currentPolygon, setCurrentPolygon] = useState([]);
  const [polygonClosed, setPolygonClosed] = useState(false);
  const [events, setEvents] = useState([]);
  const [pagination, setPagination] = useState(EMPTY_PAGINATION);
  const [resultsPage, setResultsPage] = useState(1);
  const [workerCount, setWorkerCount] = useState(0);
  const [previewVersion, setPreviewVersion] = useState(Date.now());
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const activeSourceType = connectedSource?.source_type || sourceType;
  const isStreamingSource = activeSourceType !== "image";
  const selectedPrimaryCount = enabledModels.filter(
    (modelKey) => MODELS.find((item) => item.key === modelKey)?.primary,
  ).length;

  useEffect(() => {
    if (!connectedSource?.id) {
      return;
    }
    getZones(connectedSource.id)
      .then(setSavedZones)
      .catch((error) => setMessage(error.response?.data?.detail || "Failed to load zones."));
  }, [connectedSource?.id]);

  useEffect(() => {
    if (!["running", "paused", "completed", "connected"].includes(sessionStatus)) {
      return undefined;
    }

    const intervalId = window.setInterval(async () => {
      try {
        const result = await getResults(resultsPage, RESULTS_PAGE_SIZE);
        setEvents(result.events || []);
        setWorkerCount(result.worker_count || 0);
        setSessionStatus(result.status || "idle");
        setPagination(result.pagination || EMPTY_PAGINATION);
        if (connectedSource?.source_type === "image" || result.status !== "running") {
          setPreviewVersion(Date.now());
        }
      } catch (error) {
        setMessage(error.response?.data?.detail || "Failed to fetch detection results.");
      }
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [connectedSource?.source_type, resultsPage, sessionStatus]);

  useEffect(() => {
    if (pagination.total_pages && resultsPage > pagination.total_pages) {
      setResultsPage(pagination.total_pages);
    }
  }, [pagination.total_pages, resultsPage]);

  const previewUrl = useMemo(() => {
    if (!connectedSource) {
      return "";
    }
    if (sessionStatus === "running" && connectedSource.source_type !== "image") {
      return getStreamUrl(previewVersion);
    }
    return getFrameUrl(previewVersion);
  }, [connectedSource, sessionStatus, previewVersion]);

  const connectionSummary = connectedSource
    ? `${connectedSource.source_type.toUpperCase()} | ${connectedSource.frame_width}x${connectedSource.frame_height}`
    : "";

  const canDraw = Boolean(connectedSource);

  const toggleModel = (modelKey) => {
    setEnabledModels((current) => {
      const model = MODELS.find((item) => item.key === modelKey);
      const isPrimary = Boolean(model?.primary);

      if (current.includes(modelKey)) {
        return current.filter((item) => item !== modelKey);
      }

      const currentPrimaryCount = current.filter(
        (item) => MODELS.find((modelItem) => modelItem.key === item)?.primary,
      ).length;

      if (isStreamingSource && isPrimary && currentPrimaryCount >= MAX_STREAM_MODELS) {
        return current;
      }

      const next = [...current, modelKey];
      return next;
    });
  };

  const isModelDisabled = (modelKey) => {
    if (!isStreamingSource) {
      return false;
    }

    const model = MODELS.find((item) => item.key === modelKey);
    if (!model?.primary || enabledModels.includes(modelKey)) {
      return false;
    }
    return selectedPrimaryCount >= MAX_STREAM_MODELS;
  };

  const handleConnect = async () => {
    setLoading(true);
    setMessage("");
    try {
      if (sourceType === "rtsp" && !rtspUrl.trim()) {
        setMessage("Enter an RTSP URL.");
        return;
      }
      if (sourceType !== "rtsp" && !file) {
        setMessage(`Choose a ${sourceType} file.`);
        return;
      }

      const formData = new FormData();
      formData.append("source_type", sourceType);
      if (sourceType === "rtsp") {
        formData.append("rtsp_url", rtspUrl);
      } else if (file) {
        formData.append("file", file);
      }

      const response = await connectSource(formData);
      setConnectedSource(response.source);
      setSessionStatus(response.status);
      setPreviewVersion(Date.now());
      setCurrentPolygon([]);
      setPolygonClosed(false);
      setEvents([]);
      setPagination(EMPTY_PAGINATION);
      setResultsPage(1);
      setMessage("Source connected.");
    } catch (error) {
      setMessage(error.response?.data?.detail || "Failed to connect source.");
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    if (!connectedSource) {
      setMessage("Connect a source first.");
      return;
    }
    setLoading(true);
    setMessage("");
    try {
      const response = await startInference({
        source_id: connectedSource.id,
        enabled_models: enabledModels,
      });
      setEnabledModels(response.enabled_models.filter((modelKey) => VISIBLE_MODEL_KEYS.has(modelKey)));
      setSessionStatus(response.status);
      setPreviewVersion(Date.now());
      setResultsPage(1);
      setMessage("Inference started.");
    } catch (error) {
      setMessage(error.response?.data?.detail || "Failed to start inference.");
    } finally {
      setLoading(false);
    }
  };

  const handlePauseResume = async () => {
    try {
      const response = sessionStatus === "paused" ? await resumeInference() : await pauseInference();
      setSessionStatus(response.status);
    } catch (error) {
      setMessage(error.response?.data?.detail || "Failed to update session.");
    }
  };

  const handleStop = async () => {
    try {
      const response = await stopInference();
      setSessionStatus(response.status);
      setPreviewVersion(Date.now());
    } catch (error) {
      setMessage(error.response?.data?.detail || "Failed to stop inference.");
    }
  };

  const handleSaveZone = async () => {
    if (!connectedSource || currentPolygon.length < 3) {
      return;
    }
    try {
      await saveZone({
        source_id: connectedSource.id,
        zone_type: activeZoneType,
        points: currentPolygon,
      });
      const zones = await getZones(connectedSource.id);
      setSavedZones(zones);
      setCurrentPolygon([]);
      setPolygonClosed(false);
      setMessage("Zone saved.");
    } catch (error) {
      setMessage(error.response?.data?.detail || "Failed to save zone.");
    }
  };

  const handleSnapshot = async () => {
    try {
      await saveSnapshot();
      setMessage("Snapshot saved.");
    } catch (error) {
      setMessage(error.response?.data?.detail || "Failed to save snapshot.");
    }
  };

  return (
    <div className="page">
      <header className="page-header">
        <h1>AI Model Tester</h1>
        <p>Test CCTV RTSP, image, or video with selectable AI models.</p>
      </header>

      {message ? <div className="message-banner">{message}</div> : null}

      <div className="dashboard-grid">
        <InputSourceCard
          sourceType={sourceType}
          setSourceType={setSourceType}
          rtspUrl={rtspUrl}
          setRtspUrl={setRtspUrl}
          file={file}
          setFile={setFile}
          onConnect={handleConnect}
          onStart={handleStart}
          sourceStatus={sessionStatus === "idle" ? connectedSource?.status : sessionStatus}
          disabled={loading}
          connectionSummary={connectionSummary}
        />

        <LivePreview
          previewUrl={previewUrl}
          savedZones={savedZones}
          currentPolygon={currentPolygon}
          activeZoneType={activeZoneType}
          onAddPoint={(point) => setCurrentPolygon((current) => [...current, point])}
          onFinishPolygon={() => {
            if (currentPolygon.length >= 3) {
              setPolygonClosed(true);
            }
          }}
          onPauseResume={handlePauseResume}
          onStop={handleStop}
          onSnapshot={handleSnapshot}
          sessionStatus={sessionStatus}
          canDraw={canDraw}
          workerCount={workerCount}
          polygonClosed={polygonClosed}
        />

        <div className="right-column">
          <AIModelPanel
            models={MODELS}
            enabledModels={enabledModels}
            onToggle={toggleModel}
            isDisabled={isModelDisabled}
          />
          {isStreamingSource ? (
            <div className="stream-limit-hint">Streaming mode allows up to 2 AI models at once.</div>
          ) : null}
          <ZoneTools
            activeZoneType={activeZoneType}
            setActiveZoneType={(value) => {
              setActiveZoneType(value);
              setCurrentPolygon([]);
              setPolygonClosed(false);
            }}
            currentPolygon={currentPolygon}
            onClear={() => {
              setCurrentPolygon([]);
              setPolygonClosed(false);
            }}
            onSave={handleSaveZone}
            workerCount={workerCount}
            disabled={!connectedSource}
          />
        </div>
      </div>

      <DetectionResults
        events={events}
        pagination={pagination}
        onPageChange={setResultsPage}
      />
    </div>
  );
}
