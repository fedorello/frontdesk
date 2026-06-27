import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "@/app/lib/I18nProvider";

import { Topbar } from "./Topbar";

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({
  usePathname: () => "/",
  useRouter: () => ({ push, replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

afterEach(() => {
  window.localStorage.clear();
  push.mockReset();
});

function renderTopbar() {
  return render(
    <I18nProvider>
      <Topbar />
    </I18nProvider>,
  );
}

describe("Topbar", () => {
  it("shows a Log in link when signed out", () => {
    renderTopbar();
    expect(screen.getByRole("link", { name: "Log in" })).toHaveAttribute("href", "/login");
  });

  it("shows Log out when signed in and clears the session on click", async () => {
    window.localStorage.setItem("tovayo.session", JSON.stringify({ token: "t", businessId: "b" }));
    renderTopbar();

    const logout = await screen.findByRole("button", { name: "Log out" });
    fireEvent.click(logout);

    expect(window.localStorage.getItem("tovayo.session")).toBeNull();
    expect(push).toHaveBeenCalledWith("/login");
  });
});
