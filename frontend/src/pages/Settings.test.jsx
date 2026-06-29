import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import Settings from "./Settings";

vi.mock("../services/api", () => ({
  getSettings: vi.fn(() =>
    Promise.resolve({
      model_paths: { ppe: "ai_models/ppe.pt" },
      default_confidence: 0.35,
      forklift_warning_distance: 400,
      forklift_danger_distance: 200,
      result_history_limit: 200,
      results_page_size: 10,
      max_stream_models: 2,
      zone_dependencies: { danger_zone: ["pose_anchor"] },
      runtime: { device: "cuda:0", gpu_enabled: true, half_precision: true },
    }),
  ),
}));

describe("Settings", () => {
  it("renders runtime configuration", async () => {
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    );

    await waitFor(() => expect(screen.getByText("Model Paths")).toBeInTheDocument());
    expect(screen.getByText("Thresholds")).toBeInTheDocument();
    expect(screen.getByText("Zone Dependencies")).toBeInTheDocument();
  });
});
