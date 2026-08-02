import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  locale: string;
};

type AuthState = {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isHydrated: boolean;
  setAuth: (user: User, accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
  isAuthenticated: () => boolean;
};

// SSR-safe storage. On the server `localStorage` doesn't exist; returning a
// no-op shim keeps `persist` from throwing during module init (which would
// otherwise break Next.js App Router server rendering and trigger a hydration
// mismatch loop on the client).
const ssrSafeStorage = createJSONStorage(() => {
  if (typeof window === "undefined") {
    return {
      getItem: () => null,
      setItem: () => {},
      removeItem: () => {},
    };
  }
  return window.localStorage;
});

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isHydrated: false,

      setAuth: (user, accessToken, refreshToken) =>
        set({ user, accessToken, refreshToken, isHydrated: true }),

      clearAuth: () =>
        set({ user: null, accessToken: null, refreshToken: null, isHydrated: true }),

      isAuthenticated: () => !!get().accessToken,
    }),
    {
      name: "medagent-auth",
      storage: ssrSafeStorage,
      // Defer rehydration to the client (see <AuthHydrator/>). Without this,
      // Zustand auto-rehydrates during module init, which races with React
      // hydration in the App Router and intermittently leaves `accessToken`
      // as null on the first render — sending logged-in users to /login.
      skipHydration: true,
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
      onRehydrateStorage: () => (_state, error) => {
        if (error) {
          console.error("[auth] rehydration failed", error);
        }
        useAuthStore.setState({ isHydrated: true });
      },
    },
  ),
);
