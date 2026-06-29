const SOURCE_OPTIONS = [
  { key: "rtsp", label: "RTSP URL" },
  { key: "image", label: "Image" },
  { key: "video", label: "Video" },
];

export default function InputSourceCard({
  sourceType,
  setSourceType,
  rtspUrl,
  setRtspUrl,
  file,
  setFile,
  onConnect,
  onStart,
  sourceStatus,
  disabled,
  connectionSummary,
}) {
  return (
    <section className="card">
      <div className="card-title">Input Source</div>

      <label className="field-label">Source Type</label>
      <div className="segmented-control">
        {SOURCE_OPTIONS.map((option) => (
          <button
            key={option.key}
            type="button"
            className={`segment${sourceType === option.key ? " active" : ""}`}
            onClick={() => setSourceType(option.key)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {sourceType === "rtsp" ? (
        <>
          <label className="field-label">RTSP URL</label>
          <input
            className="text-input"
            placeholder="rtsp://admin:******@192.168.1.64:554/stream1"
            value={rtspUrl}
            onChange={(event) => setRtspUrl(event.target.value)}
          />
        </>
      ) : (
        <>
          <label className="field-label">Upload {sourceType}</label>
          <label className="upload-dropzone">
            <input
              type="file"
              accept={sourceType === "image" ? "image/*" : "video/*"}
              onChange={(event) => setFile(event.target.files?.[0] || null)}
              hidden
            />
            <div className="upload-icon">⇪</div>
            <div>Drag and drop an image or video here</div>
            <div className="upload-link">or click to browse</div>
            {file ? <div className="upload-file">{file.name}</div> : null}
          </label>
        </>
      )}

      <div className="button-row">
        <button type="button" className="button button-secondary" onClick={onConnect} disabled={disabled}>
          Connect
        </button>
        <button type="button" className="button" onClick={onStart} disabled={disabled}>
          Start Test
        </button>
      </div>

      <div className="status-row">
        <span>Source Status</span>
        <span className={`status-pill ${sourceStatus === "connected" ? "success" : "muted"}`}>
          {sourceStatus || "disconnected"}
        </span>
      </div>

      {connectionSummary ? <div className="source-summary">{connectionSummary}</div> : null}
    </section>
  );
}
