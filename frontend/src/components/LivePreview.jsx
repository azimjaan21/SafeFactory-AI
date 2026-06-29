import { useEffect, useRef, useState } from "react";

function zoneColor(zoneType) {
  return zoneType === "danger_zone" ? "#ef4444" : "#22c55e";
}

export default function LivePreview({
  previewUrl,
  savedZones,
  currentPolygon,
  activeZoneType,
  onAddPoint,
  onFinishPolygon,
  onPauseResume,
  onStop,
  onSnapshot,
  sessionStatus,
  canDraw,
  workerCount,
  polygonClosed,
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    const draw = () => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) {
        return;
      }

      const width = container.clientWidth;
      const height = container.clientHeight;
      canvas.width = width;
      canvas.height = height;

      const context = canvas.getContext("2d");
      context.clearRect(0, 0, width, height);

      const drawPolygon = (points, color, dashed = false) => {
        if (!points?.length) {
          return;
        }
        context.strokeStyle = color;
        context.fillStyle = `${color}33`;
        context.lineWidth = 3;
        context.setLineDash(dashed ? [10, 6] : []);
        context.beginPath();
        points.forEach((point, index) => {
          const x = point.x * width;
          const y = point.y * height;
          if (index === 0) {
            context.moveTo(x, y);
          } else {
            context.lineTo(x, y);
          }
          context.fillStyle = color;
          context.beginPath();
          context.arc(x, y, 4, 0, Math.PI * 2);
          context.fill();
          context.fillStyle = `${color}33`;
        });
        context.beginPath();
        points.forEach((point, index) => {
          const x = point.x * width;
          const y = point.y * height;
          if (index === 0) {
            context.moveTo(x, y);
          } else {
            context.lineTo(x, y);
          }
        });
        if (!dashed && points.length >= 3) {
          context.closePath();
          context.fill();
        }
        context.stroke();
        context.setLineDash([]);
      };

      savedZones.forEach((zone) => drawPolygon(zone.points, zoneColor(zone.zone_type)));
      drawPolygon(currentPolygon, zoneColor(activeZoneType), true);

      if (workerCount > 0) {
        context.fillStyle = "#0f172a";
        context.fillRect(width - 220, height - 72, 192, 52);
        context.fillStyle = "#ffffff";
        context.font = "600 14px sans-serif";
        context.fillText("Work Zone", width - 202, height - 46);
        context.fillText(`${workerCount} workers inside`, width - 202, height - 24);
      }
    };

    draw();
    window.addEventListener("resize", draw);
    return () => window.removeEventListener("resize", draw);
  }, [savedZones, currentPolygon, activeZoneType, workerCount, previewUrl]);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(document.fullscreenElement === containerRef.current);
    };

    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  const handleClick = (event) => {
    if (!canDraw || polygonClosed || !containerRef.current) {
      return;
    }
    const rect = containerRef.current.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    onAddPoint({ x, y });
  };

  const handleFullscreenToggle = async () => {
    if (!containerRef.current) {
      return;
    }

    try {
      if (document.fullscreenElement === containerRef.current) {
        await document.exitFullscreen();
      } else {
        await containerRef.current.requestFullscreen();
      }
    } catch (error) {
      console.error("Failed to toggle fullscreen preview.", error);
    }
  };

  return (
    <section className="card preview-card">
      <div className="preview-header">
        <div className="card-title">Live Preview</div>
        <span className={`live-indicator ${sessionStatus === "running" ? "on" : ""}`}>
          {sessionStatus === "running" ? "Live" : sessionStatus || "Idle"}
        </span>
      </div>

      <div
        ref={containerRef}
        className={`preview-stage${canDraw ? " drawing-enabled" : ""}`}
        onClick={handleClick}
        onDoubleClick={onFinishPolygon}
      >
        {previewUrl ? <img src={previewUrl} alt="Preview" className="preview-image" /> : <div className="preview-placeholder">Connect a source to load preview.</div>}
        <canvas ref={canvasRef} className="preview-overlay" />
      </div>

      <div className="button-row preview-controls">
        <button type="button" className="button button-secondary" onClick={onPauseResume}>
          {sessionStatus === "paused" ? "Resume" : "Pause"}
        </button>
        <button type="button" className="button button-secondary" onClick={onStop}>
          Stop
        </button>
        <button type="button" className="button button-secondary" onClick={onSnapshot}>
          Snapshot
        </button>
        <button type="button" className="button button-secondary" onClick={handleFullscreenToggle}>
          {isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
        </button>
      </div>
    </section>
  );
}
