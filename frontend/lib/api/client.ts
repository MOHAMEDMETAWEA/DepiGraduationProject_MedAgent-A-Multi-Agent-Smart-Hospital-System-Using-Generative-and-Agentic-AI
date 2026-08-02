import { useAuthStore } from "@/store/auth";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  token?: string;
};

function getStoredRefreshToken(): string | null {
  try {
    const raw = localStorage.getItem("medagent-auth");
    if (!raw) return null;
    const state = JSON.parse(raw);
    return state.state?.refreshToken || null;
  } catch {
    return null;
  }
}

function storeNewTokens(accessToken: string, refreshToken: string) {
  // Update the live Zustand store so any subscribed React component picks
  // up the new tokens immediately. `persist` middleware mirrors this into
  // localStorage automatically, so we don't have to touch storage manually.
  try {
    useAuthStore.setState({ accessToken, refreshToken });
  } catch {
    // ignore — fall through to the direct localStorage write as a safety net
  }
  try {
    const raw = localStorage.getItem("medagent-auth");
    if (!raw) return;
    const state = JSON.parse(raw);
    state.state.accessToken = accessToken;
    state.state.refreshToken = refreshToken;
    localStorage.setItem("medagent-auth", JSON.stringify(state));
  } catch {
    // ignore
  }
}

function getAccessToken(): string | null {
  try {
    const raw = localStorage.getItem("medagent-auth");
    if (!raw) return null;
    return JSON.parse(raw).state?.accessToken || null;
  } catch {
    return null;
  }
}

let _refreshPromise: Promise<string | null> | null = null;

async function tryRefreshToken(): Promise<string | null> {
  // Prevent concurrent refresh requests (race condition)
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    const refreshToken = getStoredRefreshToken();
    if (!refreshToken) return null;

    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!res.ok) return null;

      const data = await res.json();
      storeNewTokens(data.access_token, data.refresh_token);
      return data.access_token;
    } catch {
      return null;
    } finally {
      _refreshPromise = null;
    }
  })();

  return _refreshPromise;
}

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<{ data?: T; error?: string; status: number }> {
  const { method = "GET", body, headers = {}, token } = options;

  // Use provided token, fallback to stored token from localStorage
  const authToken = token || getAccessToken();

  const makeRequest = async (authToken?: string) => {
    return fetch(`${API_BASE}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        ...headers,
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
  };

  let res = await makeRequest(authToken);

  if (res.status === 401 && path !== "/auth/refresh") {
    const newToken = await tryRefreshToken();
    if (newToken) {
      res = await makeRequest(newToken);
    }
  }

  if (res.status === 204) return { status: 204 };

  const json = await res.json();
  if (!res.ok) {
    return {
      error: json?.error?.message || json?.detail || "Request failed",
      status: res.status,
    };
  }

  return { data: json as T, status: res.status };
}
