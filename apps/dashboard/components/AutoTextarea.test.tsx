import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AutoTextarea } from "./AutoTextarea";

afterEach(cleanup);

describe("AutoTextarea", () => {
  it("renders the value and emits edits", () => {
    const onChange = vi.fn();
    render(<AutoTextarea value="hi" onChange={onChange} ariaLabel="About" />);

    const field = screen.getByLabelText("About");
    expect(field).toHaveValue("hi");

    fireEvent.change(field, { target: { value: "hello there" } });
    expect(onChange).toHaveBeenCalledWith("hello there");
  });
});
