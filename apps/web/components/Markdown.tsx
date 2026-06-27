"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Renders legal/markdown content with the site's typography.
export function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: (props) => (
          <h1 className="text-3xl font-extrabold tracking-tight" {...props} />
        ),
        h2: (props) => (
          <h2 className="mt-9 text-xl font-bold tracking-tight" {...props} />
        ),
        h3: (props) => <h3 className="mt-6 text-base font-bold" {...props} />,
        p: (props) => (
          <p
            className="mt-3 text-[15px] leading-relaxed text-muted"
            {...props}
          />
        ),
        ul: (props) => (
          <ul
            className="mt-3 list-disc space-y-1.5 pl-5 text-[15px] text-muted"
            {...props}
          />
        ),
        ol: (props) => (
          <ol
            className="mt-3 list-decimal space-y-1.5 pl-5 text-[15px] text-muted"
            {...props}
          />
        ),
        li: (props) => <li className="leading-relaxed" {...props} />,
        a: (props) => <a className="text-accent hover:underline" {...props} />,
        strong: (props) => <strong className="font-bold text-ink" {...props} />,
        blockquote: (props) => (
          <blockquote
            className="mt-4 rounded-lg border-l-4 border-accent bg-surface-2 px-4 py-2.5 text-[15px] text-muted"
            {...props}
          />
        ),
        hr: () => <hr className="my-8 border-line" />,
        code: (props) => (
          <code
            className="rounded bg-surface-3 px-1 py-0.5 font-mono text-[13px]"
            {...props}
          />
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
