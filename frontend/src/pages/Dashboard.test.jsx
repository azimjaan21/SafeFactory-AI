import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import Dashboard from "./Dashboard";

vi.mock("../services/api", () => ({
  connectSource: vi.fn(),
  getFrameUrl: vi.fn(() => "http://localhost/frame.jpg"),
  getResults: vi.fn(),
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

    expect(screen.getByText("AI Model Tester")).toBeInTheDocument();
    expect(screen.getByText("Input Source")).toBeInTheDocument();
    expect(screen.getByText("Live Preview")).toBeInTheDocument();
    expect(screen.getByText("AI Models")).toBeInTheDocument();
    expect(screen.getByText("Detection Results")).toBeInTheDocument();
  });
});
