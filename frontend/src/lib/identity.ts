const CLIENT_ID_KEY = "karaoke_client_id";
const DISPLAY_NAME_KEY = "karaoke_display_name";

function randomUuid(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  // Fallback for environments without crypto.randomUUID (older browsers/SSR test shims).
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function randomAlphanumeric(length: number): string {
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let out = "";
  for (let i = 0; i < length; i++) {
    out += chars[Math.floor(Math.random() * chars.length)];
  }
  return out;
}

// Some runtimes (and this project's own test environment) expose a global
// `localStorage` that is present but incomplete/non-functional. Every access
// goes through these helpers so a broken or absent localStorage degrades to
// an in-memory store rather than throwing.
const memoryStore = new Map<string, string>();

function storageGet(key: string): string | null {
  try {
    if (
      typeof localStorage !== "undefined" &&
      typeof localStorage.getItem === "function"
    ) {
      return localStorage.getItem(key);
    }
  } catch {
    // fall through to memory store
  }
  return memoryStore.get(key) ?? null;
}

function storageSet(key: string, value: string): void {
  try {
    if (
      typeof localStorage !== "undefined" &&
      typeof localStorage.setItem === "function"
    ) {
      localStorage.setItem(key, value);
      return;
    }
  } catch {
    // fall through to memory store
  }
  memoryStore.set(key, value);
}

/** Read the persisted client id, generating and persisting one on first use. */
export function getClientId(): string {
  const existing = storageGet(CLIENT_ID_KEY);
  if (existing) return existing;

  const id = randomUuid();
  storageSet(CLIENT_ID_KEY, id);
  return id;
}

/** Read the persisted display name, generating and persisting a default on first use. */
export function getDisplayName(): string {
  const existing = storageGet(DISPLAY_NAME_KEY);
  if (existing) return existing;

  const name = `Guest-${randomAlphanumeric(4)}`;
  storageSet(DISPLAY_NAME_KEY, name);
  return name;
}

export function setDisplayName(name: string): void {
  storageSet(DISPLAY_NAME_KEY, name);
}

/** Test-only: clear persisted identity state so each test starts fresh. */
export function __resetIdentityForTests(): void {
  memoryStore.clear();
  try {
    localStorage?.removeItem?.(CLIENT_ID_KEY);
    localStorage?.removeItem?.(DISPLAY_NAME_KEY);
  } catch {
    // ignore
  }
}
