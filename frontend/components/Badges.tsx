import { BadgeCheck, CircleDashed, Clock, PencilLine, X } from "lucide-react";
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

const REVIEW_CLASSES: Record<ReviewStatus, string> = {
  pending: "badge-gray",
  reviewed: "badge-green",
  confirmed: "badge-green",
  rejected: "badge-orange",
  edited: "badge-pink",
};

const REVIEW_TITLES: Record<ReviewStatus, string> = {
  pending: "AI analysis is ready but an HSE professional has not checked it yet",
  reviewed: "HSE reviewed the AI result and accepted it without changes",
  confirmed: "HSE verified the SIF-potential verdict",
  rejected: "HSE rejected the SIF-potential verdict — treated as not SIF-potential",
  edited: "HSE corrected AI values (priority / Life-Saving Rule / comments)",
};

const REVIEW_ICONS: Record<ReviewStatus, typeof Clock> = {
  pending: CircleDashed,
  reviewed: BadgeCheck,
  confirmed: BadgeCheck,
  rejected: X,
  edited: PencilLine,
};

export function ReviewBadge({ status }: { status: ReviewStatus }) {
  const Icon = REVIEW_ICONS[status];
  return (
    <span
      className={`badge ${REVIEW_CLASSES[status]}`}
      title={`HSE review status — ${REVIEW_TITLES[status]}`}
    >
      <Icon size={11} strokeWidth={2.4} />
      {REVIEW_LABELS[status]}
    </span>
  );
}