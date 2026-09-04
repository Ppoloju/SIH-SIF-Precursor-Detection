import type { Priority, ReviewStatus } from "@/lib/api";

export function SifBadge({ sif }: { sif: boolean }) {
  return sif ? (
    <span className="badge badge-pink">SIF</span>
  ) : (
    <span className="badge badge-gray">Non-SIF</span>
  );
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  if (priority === "HIGH") return <span className="badge badge-red">HIGH</span>;
  if (priority === "MEDIUM")
    return <span className="badge badge-orange">MEDIUM</span>;
  if (priority === "LOW") return <span className="badge badge-green">LOW</span>;
  return <span className="badge badge-gray">—</span>;
}

/** Human-readable HSE review-status labels — unambiguous wording for tables,
 *  filters and CSV exports. "HSE verified" (not merely "reviewed") is reserved
 *  for records an HSE professional has actually checked. */
export const REVIEW_LABELS: Record<ReviewStatus, string> = {
  pending: "Needs HSE review",
  reviewed: "HSE reviewed",
  confirmed: "HSE verified",
  rejected: "Rejected · not SIF",
  edited: "HSE edited",
};

/** Statuses that count as an HSE professional having checked the report. */
export const VERIFIED_STATUSES: ReviewStatus[] = [
  "confirmed",
  "reviewed",
  "edited",
];
export const isVerified = (s: ReviewStatus) => VERIFIED_STATUSES.includes(s);

// Modern status pills: a tinted background with a hairline border and a
// colored dot (pulsing gently while pending) — the pattern used by real-world
// SaaS dashboards. Colors stay semantic: slate = needs attention, green =
// checked/verified, red = rejected, brand-blue = edited.
const REVIEW_PILL: Record<ReviewStatus, string> = {
  pending: "status-pill status-pill-pending",
  reviewed: "status-pill status-pill-reviewed",
  confirmed: "status-pill status-pill-confirmed",
  rejected: "status-pill status-pill-rejected",
  edited: "status-pill status-pill-edited",
};

const REVIEW_DOT: Record<ReviewStatus, string> = {
  pending: "status-dot status-dot-pending animate-pulseDot",
  reviewed: "status-dot status-dot-reviewed",
  confirmed: "status-dot status-dot-confirmed",
  rejected: "status-dot status-dot-rejected",
  edited: "status-dot status-dot-edited",
};

const REVIEW_TITLES: Record<ReviewStatus, string> = {
  pending: "AI analysis is ready but an HSE professional has not checked it yet",
  reviewed: "HSE reviewed the AI result and accepted it without changes",
  confirmed: "HSE verified the SIF-potential verdict",
  rejected: "HSE rejected the SIF-potential verdict — treated as not SIF-potential",
  edited: "HSE corrected AI values (priority / Life-Saving Rule / comments)",
};

export function ReviewBadge({ status }: { status: ReviewStatus }) {
  return (
    <span
      className={REVIEW_PILL[status]}
      title={`HSE review status — ${REVIEW_TITLES[status]}`}
    >
      <span aria-hidden className={REVIEW_DOT[status]} />
      {REVIEW_LABELS[status]}
    </span>
  );
}