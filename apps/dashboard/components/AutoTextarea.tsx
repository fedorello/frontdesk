"use client";

import { useEffect, useRef } from "react";

// A textarea that grows to fit its content (no inner scrollbar, no manual resize).
export function AutoTextarea({
  value,
  onChange,
  ariaLabel,
  placeholder,
  className = "",
  minRows = 1,
}: {
  value: string;
  onChange: (value: string) => void;
  ariaLabel?: string;
  placeholder?: string;
  className?: string;
  minRows?: number;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (element === null) return;
    element.style.height = "auto";
    element.style.height = `${element.scrollHeight}px`;
  }, [value]);

  return (
    <textarea
      ref={ref}
      value={value}
      rows={minRows}
      aria-label={ariaLabel}
      placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)}
      className={`resize-none overflow-hidden ${className}`}
    />
  );
}
