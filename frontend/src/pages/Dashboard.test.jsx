import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import Dashboard from "./Dashboard";

vi.mock("../services/api", () => ({
  connectDemo: vi.fn(() => Promise.reject(new Error("no demo in tests"))),
  connectSource: vi.fn(),
  getFrameUrl: vi.fn(() => "http://localhost/frame.jpg"),
  getResults: vi.fn(() => Promise.reject(new Error("no results in tests"))),
  getSettings: vi.fn(() => Promise.resolve({ runtime: { gpu_enabled: false } })),
  getStreamUrl: vi.fn(() => "http://localhost/stream"),
  getZones: vi.fn(() => Promise.resolve([])),
  pauseInference: vi.fn(),
  resumeInference: vi.fn(),
  saveSnapshot: vi.fn(),
  saveZone: vi.fn(),
  startInference: vi.fn(),
  stopInference: vi.fn(),
}));

describe("Dashboard", () => {
  it("renders core dashboard sections", () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>,
    );

    expect(screen.getByText("SafeFactory AI")).toBeInTheDocument();
    expect(screen.getByText("Camera 1")).toBeInTheDocument();
    expect(screen.getByText("AI Models")).toBeInTheDocument();
    expect(screen.getByText("Recent Detections")).toBeInTheDocument();
    expect(screen.getByText("▦ Draw Zone")).toBeInTheDocument();
  });
});
