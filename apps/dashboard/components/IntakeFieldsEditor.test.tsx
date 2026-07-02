import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { IntakeField } from "@/app/lib/api";
import { I18nProvider } from "@/app/lib/I18nProvider";

import { IntakeFieldsEditor } from "./IntakeFieldsEditor";

afterEach(cleanup);

function renderEditor(value: IntakeField[], onChange: (fields: IntakeField[]) => void = () => {}) {
  return render(
    <I18nProvider>
      <IntakeFieldsEditor value={value} onChange={onChange} />
    </I18nProvider>,
  );
}

describe("IntakeFieldsEditor", () => {
  it("adds a blank field", () => {
    const onChange = vi.fn();
    renderEditor([], onChange);
    fireEvent.click(screen.getByText(/Add field/));
    expect(onChange).toHaveBeenCalledWith([
      { name: "", description: "", ask: "", normalize: "" },
    ]);
  });

  it("edits a field's name", () => {
    const onChange = vi.fn();
    renderEditor([{ name: "", description: "", ask: "", normalize: "" }], onChange);
    fireEvent.change(screen.getByLabelText("Field name (e.g. Birth date)"), {
      target: { value: "Birth date" },
    });
    expect(onChange).toHaveBeenCalledWith([
      { name: "Birth date", description: "", ask: "", normalize: "" },
    ]);
  });

  it("edits a field's normalization rule", () => {
    const onChange = vi.fn();
    renderEditor([{ name: "Birth date", description: "", ask: "", normalize: "" }], onChange);
    fireEvent.change(screen.getByLabelText(/How to format the answer/), {
      target: { value: "Format as DD.MM.YYYY" },
    });
    expect(onChange).toHaveBeenCalledWith([
      { name: "Birth date", description: "", ask: "", normalize: "Format as DD.MM.YYYY" },
    ]);
  });

  it("removes a field", () => {
    const onChange = vi.fn();
    renderEditor([{ name: "X" }], onChange);
    fireEvent.click(screen.getByText("Remove"));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it("hides Add once 5 fields exist", () => {
    renderEditor([1, 2, 3, 4, 5].map((n) => ({ name: `f${n}` })));
    expect(screen.queryByText(/Add field/)).not.toBeInTheDocument();
  });
});
