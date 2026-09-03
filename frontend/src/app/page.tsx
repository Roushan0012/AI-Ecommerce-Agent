"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  fetchHealth,
  HealthResponse,
  API_BASE_URL,
  loginUser,
  registerUser,
  fetchCurrentUser,
  logoutUser,
} from "@/lib/api";
import { AuthUser, subscribeAuth, getAuthState } from "@/lib/auth";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Authentication state
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [emailInput, setEmailInput] = useState<string>("");
  const [passwordInput, setPasswordInput] = useState<string>("");

  const checkConnection = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHealth();
      setHealth(data);
    } catch (err: unknown) {
      setHealth(null);
      setError(
        err instanceof Error
          ? err.message
          : "Failed to connect to the backend server."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;

    async function initialize() {
      try {
        const data = await fetchHealth();
        if (!ignore) {
          setHealth(data);
          setError(null);
        }
      } catch (err: unknown) {
        if (!ignore) {
          setHealth(null);
          setError(
            err instanceof Error
              ? err.message
              : "Failed to connect to the backend server."
          );
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }

      // Restore and validate session token against backend
      const user = await fetchCurrentUser();
      if (!ignore) {
        setCurrentUser(user);
      }
    }

    initialize();

    // Subscribe to client-side auth state changes
    const unsubscribe = subscribeAuth((state) => {
      if (!ignore) {
        setCurrentUser(state.user);
      }
    });

    return () => {
      ignore = true;
      unsubscribe();
    };
  }, []);

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError(null);
    setAuthSuccess(null);

    try {
      if (authMode === "login") {
        const { user } = await loginUser(emailInput, passwordInput);
        setCurrentUser(user);
        setAuthSuccess(`Welcome back, ${user.email}!`);
        setPasswordInput("");
      } else {
        await registerUser(emailInput, passwordInput);
        setAuthSuccess("Account registered! Logging in...");
        const { user } = await loginUser(emailInput, passwordInput);
        setCurrentUser(user);
        setPasswordInput("");
      }
    } catch (err: unknown) {
      setAuthError(
        err instanceof Error ? err.message : "Authentication request failed."
      );
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    logoutUser();
    setCurrentUser(null);
    setAuthSuccess(null);
    setAuthError(null);
  };

  const fillDemoMerchant = () => {
    setEmailInput("merchant@example.com");
    setPasswordInput("MerchantPassword123!");
    setAuthMode("login");
    setAuthError(null);
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-zinc-50 to-zinc-100 px-6 py-12 text-zinc-900 dark:from-zinc-950 dark:to-black dark:text-zinc-100">
      <main className="flex max-w-2xl flex-col items-center text-center">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-zinc-200 bg-white/80 px-3.5 py-1 text-xs font-medium text-zinc-700 shadow-sm backdrop-blur-sm dark:border-zinc-800 dark:bg-zinc-900/80 dark:text-zinc-300">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
          Razorpay AI Buildathon — Track 01
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight sm:text-5xl lg:text-6xl">
          AI Commerce Agent
        </h1>
        <p className="mt-6 text-lg leading-relaxed text-zinc-600 dark:text-zinc-400 sm:text-xl">
          An AI-powered agentic commerce platform for product discovery,
          recommendations, revenue growth and secure checkout.
        </p>

        {/* Backend Connection Status Section */}
        <div className="mt-8 w-full max-w-md rounded-xl border border-zinc-200 bg-white/90 p-5 shadow-sm backdrop-blur-sm transition-all dark:border-zinc-800 dark:bg-zinc-900/90 text-left">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Backend Status
            </span>
            <button
              onClick={checkConnection}
              disabled={loading}
              className="rounded-md border border-zinc-200 bg-zinc-50 px-2.5 py-1 text-xs font-medium text-zinc-700 transition hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700 cursor-pointer"
            >
              {loading ? "Checking..." : "Recheck"}
            </button>
          </div>

          <div className="mt-3">
            {loading ? (
              <div className="flex items-center gap-2.5 text-sm text-zinc-600 dark:text-zinc-400">
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400 animate-pulse"></span>
                <span>Checking backend connection...</span>
              </div>
            ) : health ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-emerald-600 dark:text-emerald-400">
                  <span className="h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
                  <span>Connected</span>
                </div>
                <div className="rounded-lg bg-zinc-50 p-2.5 text-xs text-zinc-600 dark:bg-zinc-800/60 dark:text-zinc-300 font-mono space-y-1">
                  <div className="flex justify-between">
                    <span className="text-zinc-400 dark:text-zinc-500">Service:</span>
                    <span className="font-semibold">{health.service}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400 dark:text-zinc-500">Status:</span>
                    <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                      {health.status}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-400 dark:text-zinc-500">Endpoint:</span>
                    <span className="truncate max-w-[200px]">{API_BASE_URL}/api/health</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-rose-600 dark:text-rose-400">
                  <span className="h-2.5 w-2.5 rounded-full bg-rose-500"></span>
                  <span>Unavailable</span>
                </div>
                <div className="rounded-lg bg-rose-50/70 p-2.5 text-xs text-rose-700 dark:bg-rose-950/40 dark:text-rose-300 space-y-1">
                  <p className="font-medium">Could not reach FastAPI server.</p>
                  <p className="text-[11px] text-rose-600 dark:text-rose-400">
                    {error || `Verify backend is running at ${API_BASE_URL}`}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Phase 18D - Authentication Section */}
        <div className="mt-4 w-full max-w-md rounded-xl border border-zinc-200 bg-white/90 p-5 shadow-sm backdrop-blur-sm transition-all dark:border-zinc-800 dark:bg-zinc-900/90 text-left">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
              Authentication
            </span>
            {currentUser && (
              <button
                onClick={handleLogout}
                className="rounded-md border border-rose-200 bg-rose-50 px-2 py-0.5 text-xs font-medium text-rose-700 hover:bg-rose-100 dark:border-rose-900 dark:bg-rose-950/50 dark:text-rose-300"
              >
                Log Out
              </button>
            )}
          </div>

          <div className="mt-3">
            {currentUser ? (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                    {currentUser.email}
                  </div>
                  <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-semibold text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 uppercase">
                    {currentUser.role}
                  </span>
                </div>
                <p className="text-xs text-zinc-500 dark:text-zinc-400">
                  JWT active. Protected API requests include authorization headers.
                </p>
              </div>
            ) : (
              <div>
                <div className="mb-3 flex items-center justify-between border-b border-zinc-100 pb-2 dark:border-zinc-800">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setAuthMode("login");
                        setAuthError(null);
                      }}
                      className={`text-xs font-semibold ${
                        authMode === "login"
                          ? "text-zinc-900 dark:text-white border-b-2 border-zinc-900 dark:border-white pb-1"
                          : "text-zinc-400 hover:text-zinc-600"
                      }`}
                    >
                      Log In
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setAuthMode("register");
                        setAuthError(null);
                      }}
                      className={`text-xs font-semibold ${
                        authMode === "register"
                          ? "text-zinc-900 dark:text-white border-b-2 border-zinc-900 dark:border-white pb-1"
                          : "text-zinc-400 hover:text-zinc-600"
                      }`}
                    >
                      Register
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={fillDemoMerchant}
                    className="text-[11px] font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                  >
                    Demo Merchant
                  </button>
                </div>

                <form onSubmit={handleAuthSubmit} className="space-y-2.5">
                  <div>
                    <input
                      type="email"
                      required
                      placeholder="Email address"
                      value={emailInput}
                      onChange={(e) => setEmailInput(e.target.value)}
                      className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs text-zinc-900 placeholder-zinc-400 focus:border-indigo-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                    />
                  </div>
                  <div>
                    <input
                      type="password"
                      required
                      placeholder="Password (min 8 chars)"
                      value={passwordInput}
                      onChange={(e) => setPasswordInput(e.target.value)}
                      className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs text-zinc-900 placeholder-zinc-400 focus:border-indigo-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                    />
                  </div>

                  {authError && (
                    <div className="rounded bg-rose-50 p-2 text-[11px] text-rose-600 dark:bg-rose-950/40 dark:text-rose-300">
                      {authError}
                    </div>
                  )}

                  {authSuccess && (
                    <div className="rounded bg-emerald-50 p-2 text-[11px] text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-300">
                      {authSuccess}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={authLoading}
                    className="w-full rounded-lg bg-zinc-900 py-1.5 text-xs font-semibold text-white shadow hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
                  >
                    {authLoading
                      ? "Authenticating..."
                      : authMode === "login"
                      ? "Log In with JWT"
                      : "Create Account"}
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 rounded-lg bg-zinc-900 px-4 py-2 text-xs font-semibold text-white shadow transition hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white cursor-pointer"
          >
            <span>📊</span>
            <span>Open Merchant Dashboard</span>
          </Link>
        </div>

        <div className="mt-8 flex items-center gap-3 text-xs text-zinc-500 dark:text-zinc-500">
          <span className="rounded bg-zinc-200/70 px-2 py-1 font-mono dark:bg-zinc-800">
            Next.js 16
          </span>
          <span className="rounded bg-zinc-200/70 px-2 py-1 font-mono dark:bg-zinc-800">
            FastAPI
          </span>
          <span className="rounded bg-zinc-200/70 px-2 py-1 font-mono dark:bg-zinc-800">
            JWT RBAC
          </span>
          <span className="rounded bg-zinc-200/70 px-2 py-1 font-mono dark:bg-zinc-800">
            Tailwind CSS
          </span>
        </div>
      </main>
    </div>
  );
}
