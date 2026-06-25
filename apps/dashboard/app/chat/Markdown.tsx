import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Styled via descendant utilities so react-markdown stays unconfigured (and safe:
// no raw HTML). Covers the bits the assistant actually emits — bold, lists, code.
const STYLES =
  "space-y-2 [&_strong]:font-semibold [&_ul]:ml-4 [&_ul]:list-disc [&_ul]:space-y-0.5 " +
  "[&_ol]:ml-4 [&_ol]:list-decimal [&_ol]:space-y-0.5 [&_a]:underline " +
  "[&_code]:rounded [&_code]:bg-black/10 [&_code]:px-1 dark:[&_code]:bg-white/15";

export function Markdown({ children }: { children: string }) {
  return (
    <div className={STYLES}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </div>
  );
}
