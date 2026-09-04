// Client-side CSV export helpers. Files open directly in Excel / Google Sheets
// (UTF-8 BOM + CRLF, quoted cells, arrays flattened).

function cellValue(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "number") {
    // Round long floats (e.g. 73.333…) without losing integers.
    return Math.abs(v - Math.round(v)) < 1e-9 ? String(v) : String(Math.round(v * 100) / 100);
  }
  if (Array.isArray(v)) return v.map(cellValue).filter(Boolean).join(" | ");
  if (v instanceof Date) return v.toISOString();
  return String(v).replace(/[\u0000-\u001f\u007f]/g, " ").trim();
}

export function toCsv(rows: Record<string, unknown>[]): string {
  if (rows.length === 0) return "\uFEFF";
  const cols: string[] = [];
  for (const row of rows) {
    for (const key of Object.keys(row)) {
      if (!cols.includes(key)) cols.push(key);
    }
  }
  const esc = (v: string) =>
    /[",\r\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
  const line = (vals: string[]) => vals.map(esc).join(",");
  const body = rows.map((r) => line(cols.map((c) => cellValue(r[c]))));
  return "\uFEFF" + [line(cols), ...body].join("\r\n");
}

/** Trigger a browser download for an arbitrary text payload. */
export function downloadText(
  filename: string,
  text: string,
  mime = "text/csv;charset=utf-8"
): void {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 3000);
}

export function downloadCsv(filename: string, rows: Record<string, unknown>[]): void {
  downloadText(filename, toCsv(rows));
}

export function todayStamp(): string {
  return new Date().toISOString().slice(0, 10);
}
