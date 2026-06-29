import { ImageResponse } from "next/og";

import { SITE_TITLE } from "./lib/site";

// A generated social card (no binary asset to maintain): the Tovayo mark + headline on a
// clean brand background. Next serves it at /opengraph-image and wires the og:image tag.
export const alt = SITE_TITLE;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const ACCENT = "#2563eb";
const INK = "#0e1116";
const MUTED = "#5a616e";

export default function OpengraphImage() {
  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: "#ffffff",
        padding: "80px",
        fontFamily: "sans-serif",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
        <svg width="76" height="76" viewBox="3 4 34 34" fill="none">
          <path
            d="M11 30.5 8 36.5l-.2-6.1A8 8 0 0 1 4 23.5v-10A8 8 0 0 1 12 5.5h16a8 8 0 0 1 8 8v10a8 8 0 0 1-8 8z"
            fill={ACCENT}
          />
          <circle cx="15.6" cy="16" r="2.5" fill="#fff" />
          <circle cx="24.4" cy="16" r="2.5" fill="#fff" />
          <path
            d="M14.5 21.5c1.5 2.2 3.4 3.2 5.5 3.2s4-1 5.5-3.2"
            stroke="#fff"
            strokeWidth="2.4"
            strokeLinecap="round"
          />
        </svg>
        <div style={{ fontSize: "40px", fontWeight: 800, color: INK }}>
          Tovayo
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "28px" }}>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            fontSize: "66px",
            fontWeight: 800,
            color: INK,
            lineHeight: 1.12,
          }}
        >
          <span>A free&nbsp;</span>
          <span style={{ color: ACCENT }}>AI front desk&nbsp;</span>
          <span>for your small business</span>
        </div>
        <div
          style={{
            display: "flex",
            fontSize: "30px",
            color: MUTED,
            lineHeight: 1.35,
          }}
        >
          Answers customers, books appointments, and sends reminders — 24/7, in
          their language.
        </div>
      </div>

      <div style={{ display: "flex" }}>
        <div
          style={{
            display: "flex",
            fontSize: "26px",
            fontWeight: 700,
            color: ACCENT,
            background: "#e9f0fe",
            padding: "12px 26px",
            borderRadius: "999px",
          }}
        >
          Free &amp; open source · MIT
        </div>
      </div>
    </div>,
    { ...size },
  );
}
