import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WeeklyHoursEditor } from "./WeeklyHoursEditor";

afterEach(cleanup);

describe("WeeklyHoursEditor", () => {
  it("renders seven days, all closed by default", () => {
    render(<WeeklyHoursEditor value={[]} onChange={() => {}} locale="en" closedLabel="Closed" />);
    expect(screen.getAllByRole("switch")).toHaveLength(7);
    expect(screen.getAllByText("Closed")).toHaveLength(7);
  });

  it("opening a day emits its default hours", () => {
    const onChange = vi.fn();
    render(<WeeklyHoursEditor value={[]} onChange={onChange} locale="en" closedLabel="Closed" />);

    fireEvent.click(screen.getAllByRole("switch")[0]); // Monday (weekday 0)

    expect(onChange).toHaveBeenCalledWith([{ weekday: 0, opens: "09:00:00", closes: "17:00:00" }]);
  });

  it("shows localized weekday labels and time inputs for an open day", () => {
    render(
      <WeeklyHoursEditor
        value={[{ weekday: 2, opens: "10:00:00", closes: "15:00:00" }]}
        onChange={() => {}}
        locale="en"
        closedLabel="Closed"
      />,
    );

    expect(screen.getByText("Wednesday")).toBeInTheDocument(); // Monday=0 → 2 = Wednesday
    expect(screen.getByDisplayValue("10:00")).toBeInTheDocument();
    expect(screen.getByDisplayValue("15:00")).toBeInTheDocument();
    expect(screen.getAllByText("Closed")).toHaveLength(6);
  });
});
