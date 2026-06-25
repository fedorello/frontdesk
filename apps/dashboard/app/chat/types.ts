export interface TraceStep {
  kind: "thought" | "tool";
  text?: string | null;
  tool?: string | null;
  args?: Record<string, unknown> | null;
  result?: string | null;
}

export interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  trace?: TraceStep[];
}
