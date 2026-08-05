export type Theme = "dark" | "light";

const STORAGE_KEY = "karaoke-theme";

function readStored(): Theme {
  try {
    return localStorage.getItem(STORAGE_KEY) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

function persist(theme: Theme) {
  if (typeof document !== "undefined")
    document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // storage unavailable (e.g. private mode, test environment)
  }
}

class ThemeStore {
  current: Theme = $state(readStored());

  toggle() {
    this.current = this.current === "dark" ? "light" : "dark";
    persist(this.current);
  }
}

export const themeStore = new ThemeStore();
persist(themeStore.current);
