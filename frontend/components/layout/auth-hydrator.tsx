"use client";

import { useEffect } from "react";

import { useAuthStore } from "@/store/auth";

/**
 * Triggers the Zustand `persist` rehydration once on the client.
 *
 * The auth store uses `skipHydration: true` so that no rehydration is
 * attempted during SSR / module init — that path races with React's own
 * hydration in the App Router and was leaving logged-in users with a
 * `null` access token on the first render (manifesting as an immediate
 * redirect back to /login on every page refresh).
 *
 * Mount this once near the top of the locale layout. It renders nothing.
 */
export function AuthHydrator() {
  useEffect(() => {
    void useAuthStore.persist.rehydrate();
  }, []);
  return null;
}
