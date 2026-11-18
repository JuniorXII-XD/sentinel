import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import * as client from "../src/api";
import { Auth } from "../src/shared";
import SettingsPage from "../src/pages/SettingsPage";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("shows server-provided rule parameters and explains numeric editing limits", async () => {
  vi.spyOn(client, "api").mockResolvedValue({
    environment: "development",
    session_hours: 8,
    idle_minutes: 30,
    work_start: 7,
    work_end: 22,
    timezone: "Asia/Bangkok",
    demo_enabled: false,
    rules: [
      {
        id: "AUTH-002",
        name: "Spray",
        enabled: true,
        severity: "high",
        threshold: 7,
        window_seconds: 420,
        max_attempts_per_account: 4,
      },
      {
        id: "AUTH-003",
        name: "Cluster",
        enabled: true,
        severity: "medium",
        threshold: 13,
        window_seconds: 600,
        min_accounts: 6,
        min_source_ips: 5,
      },
    ],
  });
  render(
    <Auth.Provider
      value={{
        user: { id: 2, username: "analyst", role: "analyst", is_active: true },
        setUser: () => {},
        demo: false,
        setDemo: () => {},
      }}
    >
      <SettingsPage />
    </Auth.Provider>,
  );
  expect(
    await screen.findByText(
      /minimum 7 distinct accounts · maximum 4 failures per account/,
    ),
  ).toBeTruthy();
  expect(
    screen.getByText(
      /minimum 13 failures · minimum 6 accounts · minimum 5 source IPs/,
    ),
  ).toBeTruthy();
  expect(
    screen.getByText(/Numeric parameters are read-only here/),
  ).toBeTruthy();
  for (const toggle of screen.getAllByRole("switch")) {
    expect((toggle as HTMLButtonElement).disabled).toBe(true);
  }
});
