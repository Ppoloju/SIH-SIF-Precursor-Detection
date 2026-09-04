"use client";

import { Download } from "lucide-react";
import { downloadCsv, todayStamp } from "@/lib/export";

/** Downloads `rows` as a CSV file (Excel-compatible) on click. */
export default function ExportButton({
  rows,
  filename,
  label = "Export CSV",
}: {
  rows: Record<string, unknown>[];
  filename: string;
  label?: string;
}) {
  const empty = rows.length === 0;
  return (
    <button
      onClick={() => downloadCsv(`${filename}-${todayStamp()}.csv`, rows)}
      disabled={empty}
      title={empty ? "Nothing to export yet" : `Download ${rows.length} rows as CSV`}
      className="btn-ghost disabled:cursor-not-allowed disabled:opacity-40"
    >
      <Download size={15} />
      {label}
    </button>
  );
}
