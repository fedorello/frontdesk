import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ToggleSwitch } from "./ToggleSwitch";

afterEach(cleanup);

describe("ToggleSwitch", () => {
  it("reflects its state and toggles on click", () => {
    const onChange = vi.fn();
    render(<ToggleSwitch checked={false} onChange={onChange} label="Online" />);

    const toggle = screen.getByRole("switch", { name: "Online" });
    expect(toggle).toHaveAttribute("aria-checked", "false");

    fireEvent.click(toggle);
    expect(onChange).toHaveBeenCalledWith(true);
  });
});
