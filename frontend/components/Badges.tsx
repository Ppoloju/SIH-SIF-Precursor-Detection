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
 *  filters and CSV exports. */
export const REVIEW_LABELS: Record<ReviewStatus, string> = {
  pending: "Needs HSE review",
  reviewed: "HSE reviewed",
  confirmed: "HSE confirmed",
  rejected: "SIF rejected",
  edited: "HSE edited",
};

const REVIEW_CLASSES: Record<ReviewStatus, string> = {
  pending: "badge-gray",
  reviewed: "badge-green",
  confirmed: "badge-green",
  rejected: "badge-orange",
  edited: "badge-pink",
};

const REVIEW_TITLES: Record<ReviewStatus, string> = {
  pending: "AI analysis is ready but an HSE professional has not reviewed it yet",
  reviewed: "HSE accepted the AI result without changes",
  confirmed: "HSE confirmed the SIF-potential verdict",
  rejected: "HSE rejected the SIF-potential verdict",
  edited: "HSE corrected AI values (priority / Life-Saving Rule / comments)",
};

export function ReviewBadge({ status }: { status: ReviewStatus }) {
  return (
    <span
      className={`badge ${REVIEW_CLASSES[status]}`}
      title={`HSE review status — ${REVIEW_TITLES[status]}`}
    >
      {REVIEW_LABELS[status]}
    </span>
  );
}