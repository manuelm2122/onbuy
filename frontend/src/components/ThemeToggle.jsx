import { Sun, Moon } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

export const ThemeToggle = ({ onDark = false }) => {
  const { theme, toggleTheme } = useTheme();
  const cls = onDark
    ? "border-white/15 text-slate-300 hover:text-white hover:bg-white/10"
    : "border-slate-300 text-slate-500 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800";
  return (
    <button
      type="button"
      onClick={toggleTheme}
      data-testid="theme-toggle-btn"
      aria-label={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      title={theme === "dark" ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      className={`inline-flex items-center justify-center w-9 h-9 rounded-full border transition-colors shrink-0 ${cls}`}
    >
      {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
    </button>
  );
};
