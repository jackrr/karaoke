export const SESSION_MENU_TRIGGER_KEY = Symbol("session-menu-trigger");

export type SessionMenuTrigger = { open: (() => void) | null };
