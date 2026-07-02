import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import DetectionResults from "../components/DetectionResults";
import { getResults } from "../services/api";

const PAGE_SIZE = 20;
const EMPTY_PAGINATION = { page: 1, page_size: PAGE_SIZE, total_events: 0, total_pages: 1 };

export default function DetectionsPage() {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [pagination, setPagination] = useState(EMPTY_PAGINATION);
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    let active = true;

    const fetch = async () => {
      try {
        const result = await getResults(currentPage, PAGE_SIZE);
        if (!active) return;
        setEvents(result.events || []);
        setPagination(result.pagination || EMPTY_PAGINATION);
      } catch (_) {}
    };

    fetch();
    const id = window.setInterval(fetch, 2000);
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, [currentPage]);

  return (
    <div className="page">
      <header className="page-header detections-header">
        <div className="detections-title-row">
          <button type="button" className="button button-secondary back-btn" onClick={() => navigate("/")}>
            ← Back
          </button>
          <div>
            <h1>Detection Results</h1>
            <p>Full event log — auto-refreshes every 2 seconds.</p>
          </div>
        </div>
      </header>

      <DetectionResults events={events} pagination={pagination} onPageChange={setCurrentPage} />
    </div>
  );
}
