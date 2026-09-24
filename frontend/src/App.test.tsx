import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const fetchMock = vi.fn();

describe("App", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("loads bootstrap data and renders the shell", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ policy_id: "PLUM_GHI_2024" })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          test_cases: [
            {
              case_id: "TC004",
              case_name: "Clean Consultation",
              description: "A good claim.",
              input: {
                member_id: "EMP001",
                policy_id: "PLUM_GHI_2024",
                claim_category: "CONSULTATION",
                treatment_date: "2024-11-01",
                claimed_amount: 1500,
                documents: []
              }
            }
          ]
        })
      });

    render(<App />);

    expect(await screen.findByText(/Plum Claims Pipeline Showcase/i)).toBeInTheDocument();
    expect(await screen.findByText("PLUM_GHI_2024")).toBeInTheDocument();
  });

  it("loads a test case into the form", async () => {
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ policy_id: "PLUM_GHI_2024" })
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          test_cases: [
            {
              case_id: "TC010",
              case_name: "Network Hospital",
              description: "Network case.",
              input: {
                member_id: "EMP010",
                policy_id: "PLUM_GHI_2024",
                claim_category: "CONSULTATION",
                treatment_date: "2024-11-03",
                claimed_amount: 4500,
                hospital_name: "Apollo Hospitals",
                documents: []
              }
            }
          ]
        })
      });

    render(<App />);
    await screen.findByText(/Plum Claims Pipeline Showcase/i);

    fireEvent.change(screen.getByLabelText(/Load test case/i), {
      target: { value: "TC010" }
    });

    await waitFor(() => {
      expect(screen.getByDisplayValue("EMP010")).toBeInTheDocument();
      expect(screen.getByDisplayValue("Apollo Hospitals")).toBeInTheDocument();
    });
  });
});
