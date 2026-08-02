import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "./auth";

const sampleUser = {
  id: "u-1",
  email: "patient@example.com",
  full_name: "Test Patient",
  role: "patient",
  locale: "ar",
};

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.getState().clearAuth();
  });

  it("starts unauthenticated by default", () => {
    expect(useAuthStore.getState().isAuthenticated()).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("setAuth populates user + tokens and flips isAuthenticated", () => {
    useAuthStore.getState().setAuth(sampleUser, "access-xyz", "refresh-abc");
    const s = useAuthStore.getState();
    expect(s.user).toEqual(sampleUser);
    expect(s.accessToken).toBe("access-xyz");
    expect(s.refreshToken).toBe("refresh-abc");
    expect(s.isAuthenticated()).toBe(true);
  });

  it("clearAuth wipes user + tokens", () => {
    useAuthStore.getState().setAuth(sampleUser, "a", "b");
    useAuthStore.getState().clearAuth();
    const s = useAuthStore.getState();
    expect(s.user).toBeNull();
    expect(s.accessToken).toBeNull();
    expect(s.refreshToken).toBeNull();
    expect(s.isAuthenticated()).toBe(false);
  });

  it("isHydrated is true after any auth mutation", () => {
    useAuthStore.getState().setAuth(sampleUser, "a", "b");
    expect(useAuthStore.getState().isHydrated).toBe(true);
  });
});
