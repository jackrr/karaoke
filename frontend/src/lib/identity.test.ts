import { describe, it, expect, beforeEach } from "vitest";
import {
  getClientId,
  getDisplayName,
  setDisplayName,
  __resetIdentityForTests,
} from "./identity";

describe("identity", () => {
  beforeEach(() => {
    __resetIdentityForTests();
  });

  describe("getClientId", () => {
    it("generates a non-empty id on first call", () => {
      const id = getClientId();
      expect(id).toBeTruthy();
    });

    it("returns the same id across calls", () => {
      const first = getClientId();
      const second = getClientId();
      expect(second).toBe(first);
    });
  });

  describe("getDisplayName", () => {
    it("generates a default Guest-XXXX name on first call", () => {
      const name = getDisplayName();
      expect(name).toMatch(/^Guest-[A-Za-z0-9]{4}$/);
    });

    it("returns the persisted name across calls", () => {
      const first = getDisplayName();
      const second = getDisplayName();
      expect(second).toBe(first);
    });
  });

  describe("setDisplayName", () => {
    it("persists a custom display name", () => {
      setDisplayName("Alice");
      expect(getDisplayName()).toBe("Alice");
    });
  });
});
