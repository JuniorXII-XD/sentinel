import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import * as client from "../src/api";
import { Auth, Workspace } from "../src/shared";
import AlertDetail from "../src/pages/AlertDetail";
import Events from "../src/pages/Events";
const alert = {
  id: 7,
  rule_id: "AUTH-001",
  severity: "high",
  status: "open",
  description: "Repeated login failures: suspicious signal",
  created_at: "2026-11-17T05:00:00Z",
  updated_at: "2026-11-17T05:00:00Z",
  subject: "192.0.2.1",
  is_demo: true,
  events: [],
  history: [],
};
afterEach(cleanup);
function renderAlert(role: "admin" | "analyst") {
  return render(
    <Auth.Provider
      value={{
        user: { id: 1, username: "test", role, is_active: true },
        setUser: () => {},
        demo: true,
        setDemo: () => {},
      }}
    >
      <MemoryRouter initialEntries={["/alerts/7"]}>
        <AlertDetail />
      </MemoryRouter>
    </Auth.Provider>,
  );
}
it("analysts see evidence and read-only guidance without edit controls", async () => {
  vi.spyOn(client, "api").mockResolvedValue(alert);
  renderAlert("analyst");
  expect(await screen.findByText("Related evidence")).toBeTruthy();
  expect(
    screen.queryByRole("button", { name: "Save investigation" }),
  ).toBeNull();
  expect(
    screen.getByText("Administrator access required to edit"),
  ).toBeTruthy();
});
it("admins submit notes with the concurrency timestamp and refresh evidence", async () => {
  const mock = vi
    .spyOn(client, "api")
    .mockImplementation(async (path, opts) =>
      opts?.method === "PATCH" ? { ...alert, status: "investigating" } : alert,
    );
  renderAlert("admin");
  await screen.findByText("Related evidence");
  await userEvent.selectOptions(
    screen.getByLabelText("Status"),
    "investigating",
  );
  await userEvent.type(
    screen.getByLabelText("Investigation note"),
    "Reviewed synthetic evidence.",
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Save investigation" }),
  );
  await waitFor(() =>
    expect(mock.mock.calls.some(([, o]) => o?.method === "PATCH")).toBe(true),
  );
  const [, options] = mock.mock.calls.find(([, o]) => o?.method === "PATCH")!;
  expect(JSON.parse(options!.body as string)).toEqual({
    status: "investigating",
    note: "Reviewed synthetic evidence.",
    expected_updated_at: alert.updated_at,
  });
});
it("event filters use API parameters and display an empty state", async () => {
  const mock = vi
    .spyOn(client, "api")
    .mockResolvedValue({ items: [], total: 0 });
  render(
    <Workspace.Provider value={{ scope: "demo", days: 7, revision: 0 }}>
      <Events />
    </Workspace.Provider>,
  );
  expect(await screen.findByText("No records in this view.")).toBeTruthy();
  await userEvent.selectOptions(screen.getByLabelText("Severity"), "critical");
  await waitFor(() =>
    expect(
      mock.mock.calls.some(
        ([path]) =>
          path.includes("severity=critical") && path.includes("scope=demo"),
      ),
    ).toBe(true),
  );
});
