// The assistant writes light Markdown; the dashboard shows plain text. These helpers
// drop the markup so previews and bubbles read cleanly (emoji are kept on purpose).

// Remove emphasis/code/heading/quote markers and unwrap links — newlines preserved.
export function stripMarkdown(text: string): string {
  return text
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // [label](url) → label
    .replace(/[*_`~#>]/g, "");
}

// A single-line, whitespace-collapsed version for list previews.
export function plainPreview(text: string): string {
  return stripMarkdown(text).replace(/\s+/g, " ").trim();
}
