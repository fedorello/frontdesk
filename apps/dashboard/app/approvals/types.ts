export type ApprovalDecision = "approve" | "reject";

export interface Approval {
  id: string;
  business: string;
  summary: string;
  requestedAt: string;
}
