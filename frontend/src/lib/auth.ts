/**
 * Frontend Authentication & JWT Handling (Phase 18D).
 *
 * Implements client-side authentication state, token storage, expiry detection,
 * and reactive listener subscriptions for Next.js.
 *
 * SECURITY GUARANTEES:
 * - Stores only the JWT access token string in client storage.
 * - Never includes or references backend secrets.
 * - Never sends or references machine agent keys.
 * - Treats client-side decoded roles as UI convenience only; the backend remains
 *   the authoritative RBAC boundary.
 */

export type UserRole = "customer" | "merchant" | "admin";

export interface AuthUser {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface DecodedJwtPayload {
  sub?: string;
  role?: UserRole;
  exp?: number;
  iat?: number;
}

export const TOKEN_STORAGE_KEY = "ai_agent_access_token";
export const USER_STORAGE_KEY = "ai_agent_auth_user";

// Safe SSR-aware storage helpers
export function getStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
    notifyAuthListeners();
  } catch {
    // Storage quota or privacy restriction fallback
  }
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    notifyAuthListeners();
  } catch {
    // Ignore
  }
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user: AuthUser): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
    notifyAuthListeners();
  } catch {
    // Ignore
  }
}

export function clearAuth(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
  } catch {
    // Ignore
  }
  notifyAuthListeners();
}

/**
 * Decodes standard JWT payload claims (base64url) on the client for expiry
 * checks and non-authoritative UI rendering.
 */
export function decodeJwtPayload(token: string): DecodedJwtPayload | null {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) {
      return null;
    }
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

/**
 * Checks whether a JWT token is expired or about to expire within 5 seconds.
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") {
    return true;
  }
  // exp is seconds since epoch, Date.now() is milliseconds
  return payload.exp * 1000 <= Date.now() + 5000;
}

/**
 * Event-based subscription for reactive auth updates across React components.
 */
type AuthListener = (state: AuthState) => void;
const listeners = new Set<AuthListener>();

export function subscribeAuth(listener: AuthListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getAuthState(): AuthState {
  const token = getStoredToken();
  const user = getStoredUser();
  const valid = Boolean(token && !isTokenExpired(token));

  return {
    token: valid ? token : null,
    user: valid ? user : null,
    isAuthenticated: valid,
    isLoading: false,
  };
}

export function notifyAuthListeners(): void {
  const state = getAuthState();
  listeners.forEach((listener) => {
    try {
      listener(state);
    } catch {
      // Ignore listener error
    }
  });
}
