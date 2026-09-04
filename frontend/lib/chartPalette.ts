export interface ChartPalette {
  /** cartesian grid line */
  grid: string;
  /** axis stroke */
  axis: string;
  /** tooltip cursor line / focus accent */
  focus: string;
  /** SIF-potential series */
  sif: string;
  /** "All reports" series */
  all: string;
  /** vertical-bar cursor fill */
  barCursor: string;
  /** Life-Saving Rule pie-chart segments */
  pie: string[];
}

export function chartPalette(mode: "light" | "dark"): ChartPalette {
  return mode === "dark"
    ? {
        grid: "#1c2a44",
        axis: "#4c5b75",
        focus: "#8fb5e2",
        sif: "#a3c6ec",
        all: "#4d6b93",
        barCursor: "#16233c",
        pie: ["#a3c6ec", "#d89b72", "#9ac9a8", "#c4a7e7", "#e4c77b", "#76c4c7"],
      }
    : {
        grid: "#e4ebf4",
        axis: "#94a3b8",
        focus: "#4178ae",
        sif: "#2e5f94",
        all: "#98bade",
        barCursor: "#eef4fb",
        pie: ["#2e5f94", "#b8663d", "#438a60", "#8064a8", "#b68a1a", "#247f82"],
      };
}
