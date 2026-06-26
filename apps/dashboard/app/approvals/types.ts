import type { RiskTier } from "@fedorello/airlock";

export type ApprovalDecision = "approve" | "reject";

// Shaped by the airlock approval contract (mirrors the API's ApprovalView).
export interface Approval {
  id: string;
  summary: string;
  tool: string;
  args: Record<string, unknown>;
  risk: RiskTier;
}
