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

export function ReviewBadge({ status }: { status: ReviewStatus }) {
  const map: Record<ReviewStatus, string> = {
    pending: "badge-gray",
    reviewed: "badge-green",
    confirmed: "badge-green",
    rejected: "badge-orange",
    edited: "badge-pink",
  };
  const label: Record<ReviewStatus, string> = {
    pending: "Pending",
    reviewed: "Reviewed",
    confirmed: "Confirmed",
    rejected: "Rejected",
    edited: "Edited",
  };
  return <span className={`badge ${map[status]}`}>{label[status]}</span>;
}