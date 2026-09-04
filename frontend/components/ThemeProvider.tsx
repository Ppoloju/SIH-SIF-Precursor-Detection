"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type ThemeMode = "light" | "dark";

const ThemeContext = createContext<ThemeMode>("light");

/**
 * Tracks the active theme (`.dark` on <html>). The Nav toggle flips the class
 * and dispatches a `sif-theme` event; components that draw SVG with literal
 * colors (charts) subscribe through this provider to re-render on switch.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>("light");

  useEffect(() => {
    const sync = () =>
      setMode(
        document.documentElement.classList.contains("dark") ? "dark" : "light"
      );
    sync();
    window.addEventListener("sif-theme", sync);
    return () => window.removeEventListener("sif-theme", sync);
  }, []);

  return (
    <ThemeContext.Provider value={mode}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeMode {
  return useContext(ThemeContext);
}
