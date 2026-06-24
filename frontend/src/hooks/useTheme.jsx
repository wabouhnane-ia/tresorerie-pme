import { createContext, useContext, useEffect, useState, useSyncExternalStore } from "react";

// Create a simple store to avoid hydration mismatch
function createThemeStore() {
  let listeners = new Set();
  let currentTheme = (() => {
    if (typeof window === "undefined") return "light";
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme) return savedTheme;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  })();

  return {
    get: () => currentTheme,
    set: (newTheme) => {
      if (newTheme === "light" || newTheme === "dark") {
        currentTheme = newTheme;
        listeners.forEach((l) => l());
      }
    },
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

const themeStore = createThemeStore();

const ThemeContext = createContext({
  theme: "light",
  toggleTheme: () => {},
  setTheme: () => {},
});

export function ThemeProvider({ children }) {
  const theme = useSyncExternalStore(
    themeStore.subscribe,
    themeStore.get,
    () => "light" // Server snapshot
  );

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    themeStore.set(theme === "light" ? "dark" : "light");
  };

  const setTheme = (newTheme) => {
    themeStore.set(newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return context;
}
