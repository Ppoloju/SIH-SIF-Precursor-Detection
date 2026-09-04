"use client";

import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Download, FileSpreadsheet, X } from "lucide-react";
import { cellValue, downloadText, toCsv, todayStamp } from "@/lib/export";

/** Rows shown in the preview table (the download always contains all rows). */
const PREVIEW_MAX_ROWS = 25;
/** Preview cells are truncated; the downloaded CSV keeps the full values. */
const CELL_MAX_CHARS = 140;

/**
 * Export button with a CSV preview: clicking it opens a dialog showing the
 * exact rows/columns that will be written, then downloads on confirmation —
 * so the user can view the CSV file content before exporting it.
 */
export default function ExportButton({
  rows,
  filename,
  label = "Export CSV",
}: {
  rows: Record<string, unknown>[];
  filename: string;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const empty = rows.length === 0;
  const outName = `${filename}-${todayStamp()}.csv`;

  // Build the CSV exactly once — the preview mirrors what gets downloaded.
  const csv = useMemo(() => toCsv(rows), [rows]);
  const columns = useMemo(() => {
    const cols: string[] = [];
    for (const row of rows) {
      for (const key of Object.keys(row)) {
        if (!cols.includes(key)) cols.push(key);
      }
    }
    return cols;
  }, [rows]);

  // Close on Escape and lock body scroll while the dialog is open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open]);

  const previewText = (v: unknown): string => {
    const text = cellValue(v);
    return text.length > CELL_MAX_CHARS
      ? `${text.slice(0, CELL_MAX_CHARS)}…`
      : text;
  };

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={empty}
        title={
          empty
            ? "Nothing to export yet"
            : `Preview ${rows.length} rows as CSV, then download`
        }
        className="btn-ghost disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Download size={15} />
        {label}
      </button>

      {/* Portaled so the dialog never nests inside a <p>/<div> wherever the
          trigger button is placed (invalid HTML caused React hydration errors). */}
      {open &&
        createPortal(
          <div
            className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-ink/60 p-4 backdrop-blur-sm"
            onClick={() => setOpen(false)}
            role="dialog"
            aria-modal="true"
            aria-label={`Preview ${outName}`}
          >
            <div
              className="w-full max-w-4xl animate-rise overflow-hidden rounded-3xl bg-white shadow-card"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="relative border-b border-brand-100 bg-gradient-to-br from-brand-50 via-white to-white px-6 py-5">
                <div className="flex items-center gap-3 pr-10">
                  <span className="grid h-11 w-11 flex-shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white shadow-md">
                    <FileSpreadsheet size={20} />
                  </span>
                  <div className="min-w-0">
                    <h2 className="text-lg font-extrabold tracking-tight">
                      Preview CSV before export
                    </h2>
                    <p className="mt-0.5 font-mono text-xs text-ink-muted">
                      {outName}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setOpen(false)}
                  aria-label="Close"
                  className="absolute right-4 top-4 grid h-8 w-8 place-items-center rounded-lg border border-brand-200 bg-white text-ink-soft transition hover:bg-brand-50 hover:text-brand-700"
                >
                  <X size={16} />
                </button>
              </div>

              <div className="px-6 py-4">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-soft">
                  <span>
                    <b className="text-ink">{rows.length}</b> row
                    {rows.length === 1 ? "" : "s"}
                  </span>
                  <span>
                    <b className="text-ink">{columns.length}</b> column
                    {columns.length === 1 ? "" : "s"}
                  </span>
                  {rows.length > PREVIEW_MAX_ROWS && (
                    <span className="text-ink-muted">
                      Showing first {PREVIEW_MAX_ROWS} rows — the download
                      contains all of them.
                    </span>
                  )}
                  <span className="text-ink-muted">
                    UTF-8 CSV · opens in Excel / Google Sheets
                  </span>
                </div>

                {columns.length === 0 ? (
                  <p className="mt-4 rounded-xl bg-brand-50/60 p-4 text-center text-sm text-ink-muted">
                    No data rows to export.
                  </p>
                ) : (
                  <div className="table-wrap mt-3 max-h-[52vh] overflow-auto">
                    <table className="w-full min-w-[720px] text-left text-xs">
                      <thead className="sticky top-0 bg-white">
                        <tr className="table-head">
                          <th className="px-3 py-2 font-semibold">#</th>
                          {columns.map((c) => (
                            <th key={c} className="px-3 py-2 font-semibold">
                              {c}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {rows.slice(0, PREVIEW_MAX_ROWS).map((row, i) => (
                          <tr key={i} className="table-row align-top">
                            <td className="px-3 py-2 font-mono text-[10px] text-ink-muted">
                              {i + 1}
                            </td>
                            {columns.map((c) => {
                              const text = previewText(row[c]);
                              return (
                                <td
                                  key={c}
                                  className="max-w-[260px] px-3 py-2 text-ink-soft"
                                  title={text.length < (cellValue(row[c])).length ? cellValue(row[c]) : undefined}
                                >
                                  {text || <span className="italic text-ink-muted">—</span>}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <p className="mt-3 text-[11px] leading-relaxed text-ink-muted">
                  Values are truncated in this preview only for readability —
                  the downloaded file contains every row with the full cell
                  values, ready for Excel, Google Sheets or re-import.
                </p>
              </div>

              <div className="flex flex-wrap items-center justify-end gap-3 border-t border-brand-100 bg-brand-50/50 px-6 py-3.5">
                <button onClick={() => setOpen(false)} className="btn-ghost">
                  Cancel
                </button>
                <button
                  onClick={() => {
                    downloadText(outName, csv);
                    setOpen(false);
                  }}
                  className="btn-primary"
                >
                  <Download size={15} /> Download CSV ({rows.length} row
                  {rows.length === 1 ? "" : "s"})
                </button>
              </div>
            </div>
          </div>,
          document.body
        )}
    </>
  );
}
