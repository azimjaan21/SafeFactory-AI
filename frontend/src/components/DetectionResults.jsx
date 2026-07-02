const MODEL_LABELS = {
  ppe: "PPE Detection",
  work_situation: "Work Situation Classification",
  smoke_fire: "Smoke & Fire Detection",
  worker_forklift: "Worker-Forklift Detection",
  danger_zone: "Danger Zone Detection",
  work_zone: "Work Zone Detection",
  fall_detection: "Fall Detection",
  running_detection: "Unsafe Running Detection",
  inactivity_detection: "Inactivity Detection",
  abnormal_behavior: "Abnormal Behavior Detection",
};

export default function DetectionResults({ events, pagination, onPageChange }) {
  return (
    <section className="card results-card">
      <div className="card-title">Detection Results</div>
      <div className="results-table-wrapper">
        <table className="results-table">
          <thead>
            <tr>
              <th>Detected Event</th>
              <th>Model</th>
              <th>Severity</th>
              <th>Confidence</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {events.length ? (
              events.map((event) => (
                <tr key={event.id}>
                  <td>{event.label}</td>
                  <td>{MODEL_LABELS[event.model_key] || event.model_key}</td>
                  <td>
                    <span className={`severity-badge severity-${event.severity.toLowerCase()}`}>{event.severity}</span>
                  </td>
                  <td>{typeof event.confidence === "number" ? `${(event.confidence * 100).toFixed(1)}%` : "-"}</td>
                  <td>{new Date(event.timestamp).toLocaleString()}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="5" className="empty-cell">
                  No detections yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {pagination?.total_pages > 1 ? (
        <div className="pagination">
          {Array.from({ length: pagination.total_pages }, (_, index) => index + 1).map((page) => (
            <button
              key={page}
              type="button"
              className={`page-button${page === pagination.page ? " active" : ""}`}
              onClick={() => onPageChange(page)}
            >
              {page}
            </button>
          ))}
        </div>
      ) : null}
    </section>
  );
}
