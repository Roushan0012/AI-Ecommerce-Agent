"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  DashboardActivityItem,
  DashboardOrderItem,
  OverviewMetricsResponse,
  fetchCurrentUser,
  fetchDashboardActivity,
  fetchDashboardOrders,
  fetchDashboardOverview,
  loginUser,
  logoutUser,
} from "@/lib/api";
import { AuthUser, getAuthState, subscribeAuth } from "@/lib/auth";

export default function MerchantDashboard() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [authChecking, setAuthChecking] = useState<boolean>(true);
  const [metrics, setMetrics] = useState<OverviewMetricsResponse | null>(null);
  const [orders, setOrders] = useState<DashboardOrderItem[]>([]);
  const [activities, setActivities] = useState<DashboardActivityItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Merchant login gate state
  const [loginEmail, setLoginEmail] = useState<string>("");
  const [loginPassword, setLoginPassword] = useState<string>("");
  const [loginLoading, setLoginLoading] = useState<boolean>(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  const loadDashboardData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewData, ordersData, activityData] = await Promise.all([
        fetchDashboardOverview(),
        fetchDashboardOrders(1, 10),
        fetchDashboardActivity(10),
      ]);
      setMetrics(overviewData);
      setOrders(ordersData.items || []);
      setActivities(activityData.items || []);
      setLastUpdated(new Date());
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to fetch merchant dashboard data from backend."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;

    async function initAuthAndData() {
      setAuthChecking(true);
      const user = await fetchCurrentUser();
      if (!ignore) {
        setCurrentUser(user);
        setAuthChecking(false);
        if (user && (user.role === "merchant" || user.role === "admin")) {
          loadDashboardData();
        } else {
          setLoading(false);
        }
      }
    }

    initAuthAndData();

    const unsubscribe = subscribeAuth((state) => {
      if (!ignore) {
        setCurrentUser(state.user);
        if (!state.user || (state.user.role !== "merchant" && state.user.role !== "admin")) {
          setMetrics(null);
          setOrders([]);
          setActivities([]);
        }
      }
    });

    return () => {
      ignore = true;
      unsubscribe();
    };
  }, [loadDashboardData]);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError(null);

    try {
      const { user } = await loginUser(loginEmail, loginPassword);
      setCurrentUser(user);
      setLoginPassword("");
      if (user.role === "merchant" || user.role === "admin") {
        await loadDashboardData();
      }
    } catch (err: unknown) {
      setLoginError(
        err instanceof Error ? err.message : "Authentication failed."
      );
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    logoutUser();
    setCurrentUser(null);
    setMetrics(null);
    setOrders([]);
    setActivities([]);
  };

  const fillDemoMerchant = () => {
    setLoginEmail("merchant@example.com");
    setLoginPassword("MerchantPassword123!");
    setLoginError(null);
  };

  const formatCurrency = (amount: string | number | undefined) => {
    const num = Number(amount || 0);
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(num);
  };

  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return dateStr;
    }
  };

  const isAuthorized =
    currentUser && (currentUser.role === "merchant" || currentUser.role === "admin");

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-100">
      {/* Navigation Header */}
      <header className="sticky top-0 z-30 border-b border-zinc-200 bg-white/80 backdrop-blur-md dark:border-zinc-800 dark:bg-zinc-900/80">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="rounded-lg bg-zinc-100 px-2.5 py-1 text-xs font-medium text-zinc-600 transition hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700"
            >
              ← Back
            </Link>
            <h1 className="text-xl font-bold tracking-tight">Merchant Dashboard</h1>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Live Backend
            </span>
          </div>

          <div className="flex items-center gap-3">
            {currentUser && (
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-zinc-600 dark:text-zinc-300">
                  {currentUser.email}
                </span>
                <span className="rounded bg-indigo-100 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300 uppercase">
                  {currentUser.role}
                </span>
                <button
                  onClick={handleLogout}
                  className="rounded-md border border-zinc-200 bg-white px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200"
                >
                  Log Out
                </button>
              </div>
            )}
            {lastUpdated && isAuthorized && (
              <span className="text-xs text-zinc-400 dark:text-zinc-500">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            {isAuthorized && (
              <button
                onClick={loadDashboardData}
                disabled={loading}
                className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700 cursor-pointer"
              >
                {loading ? "Refreshing..." : "Refresh"}
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
        {/* Authentication Gate / Login Card */}
        {authChecking ? (
          <div className="flex justify-center p-12">
            <span className="text-xs text-zinc-500">Checking authentication...</span>
          </div>
        ) : !currentUser ? (
          <div className="mx-auto max-w-md rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900 text-left">
            <div className="mb-4">
              <h2 className="text-base font-bold text-zinc-900 dark:text-white">
                Merchant Authentication Required
              </h2>
              <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
                Access to the Merchant Dashboard requires a verified merchant or admin JWT.
              </p>
            </div>

            <form onSubmit={handleLoginSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  placeholder="merchant@example.com"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder-zinc-400 focus:border-indigo-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  required
                  placeholder="Password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs text-zinc-900 placeholder-zinc-400 focus:border-indigo-500 focus:outline-none dark:border-zinc-700 dark:bg-zinc-800 dark:text-white"
                />
              </div>

              {loginError && (
                <div className="rounded bg-rose-50 p-2 text-xs text-rose-600 dark:bg-rose-950/40 dark:text-rose-300">
                  {loginError}
                </div>
              )}

              <div className="flex gap-2 pt-1">
                <button
                  type="submit"
                  disabled={loginLoading}
                  className="flex-1 rounded-lg bg-zinc-900 py-2 text-xs font-semibold text-white shadow hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white"
                >
                  {loginLoading ? "Authenticating..." : "Log In as Merchant"}
                </button>
                <button
                  type="button"
                  onClick={fillDemoMerchant}
                  className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs font-medium text-zinc-700 hover:bg-zinc-100 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                >
                  Demo
                </button>
              </div>
            </form>
          </div>
        ) : currentUser.role !== "merchant" && currentUser.role !== "admin" ? (
          <div className="mx-auto max-w-md rounded-2xl border border-amber-200 bg-amber-50 p-6 shadow-sm dark:border-amber-900/50 dark:bg-amber-950/40 text-left">
            <h2 className="text-sm font-bold text-amber-900 dark:text-amber-200">
              Access Forbidden (Role: {currentUser.role})
            </h2>
            <p className="mt-2 text-xs text-amber-800 dark:text-amber-300">
              Your account is logged in as a <strong>customer</strong>. The Merchant Dashboard is
              restricted to <strong>merchant</strong> and <strong>admin</strong> accounts.
            </p>
            <div className="mt-4 flex gap-2">
              <button
                onClick={handleLogout}
                className="rounded-lg bg-amber-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-800 dark:bg-amber-200 dark:text-amber-900"
              >
                Log Out & Switch Account
              </button>
              <Link
                href="/"
                className="rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-medium text-amber-900 hover:bg-amber-50 dark:border-amber-800 dark:bg-zinc-900 dark:text-amber-200"
              >
                Back to Store
              </Link>
            </div>
          </div>
        ) : (
          <>
            {/* Error Notification */}
            {error && (
              <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 dark:border-rose-900/50 dark:bg-rose-950/40">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 text-rose-700 dark:text-rose-300">
                    <span className="text-lg">⚠️</span>
                    <span className="text-sm font-medium">{error}</span>
                  </div>
                  <button
                    onClick={loadDashboardData}
                    className="rounded-md bg-rose-600 px-3 py-1 text-xs font-medium text-white hover:bg-rose-700"
                  >
                    Retry
                  </button>
                </div>
              </div>
            )}

            {/* Section 1: Overview Metrics */}
            <section>
              <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-4">
                Commerce Overview
              </h2>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {/* Total Revenue */}
                <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                  <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Total Revenue</div>
                  <div className="mt-2 text-2xl font-bold tracking-tight text-emerald-600 dark:text-emerald-400">
                    {loading ? "—" : formatCurrency(metrics?.total_revenue)}
                  </div>
                  <div className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                    {metrics?.paid_orders_count || 0} paid order(s)
                  </div>
                </div>

                {/* Paid Orders */}
                <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                  <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Completed Orders</div>
                  <div className="mt-2 text-2xl font-bold tracking-tight">
                    {loading ? "—" : metrics?.paid_orders_count || 0}
                  </div>
                  <div className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                    Out of {metrics?.total_orders_count || 0} total order(s)
                  </div>
                </div>

                {/* Conversion Rate */}
                <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                  <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Cart Conversion Rate</div>
                  <div className="mt-2 text-2xl font-bold tracking-tight text-indigo-600 dark:text-indigo-400">
                    {loading ? "—" : `${metrics?.conversion_rate || 0}%`}
                  </div>
                  <div className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                    Paid orders / initiated carts
                  </div>
                </div>

                {/* Average Order Value */}
                <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
                  <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Average Order Value</div>
                  <div className="mt-2 text-2xl font-bold tracking-tight">
                    {loading ? "—" : formatCurrency(metrics?.average_order_value)}
                  </div>
                  <div className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                    Per completed checkout
                  </div>
                </div>
              </div>
            </section>

            {/* Section 2: AI Attribution Metrics */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                  AI Attribution & Growth Engine
                </h2>
                <span className="text-xs font-medium text-purple-600 dark:text-purple-400 bg-purple-50 dark:bg-purple-950/50 px-2.5 py-0.5 rounded-full border border-purple-200 dark:border-purple-800/40">
                  Autonomous Agent Analytics
                </span>
              </div>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {/* AI Assisted Revenue */}
                <div className="rounded-xl border border-purple-100 bg-purple-50/40 p-5 shadow-sm dark:border-purple-900/30 dark:bg-purple-950/20">
                  <div className="text-xs font-medium text-purple-700 dark:text-purple-300">AI-Attributed Revenue</div>
                  <div className="mt-2 text-2xl font-bold tracking-tight text-purple-700 dark:text-purple-300">
                    {loading ? "—" : formatCurrency(metrics?.ai_assisted_revenue)}
                  </div>
                  <div className="mt-1 text-xs text-purple-600/70 dark:text-purple-400/70">
                    {metrics?.ai_assisted_percentage || 0}% of platform revenue
                  </div>
                </div>

                {/* AI Assisted Orders */}
                <div className="rounded-xl border border-purple-100 bg-purple-50/40 p-5 shadow-sm dark:border-purple-900/30 dark:bg-purple-950/20">
                  <div className="text-xs font-medium text-purple-700 dark:text-purple-300">AI-Assisted Orders</div>
                  <div className="mt-2 text-2xl font-bold tracking-tight text-purple-700 dark:text-purple-300">
                    {loading ? "—" : metrics?.ai_assisted_orders_count || 0}
                  </div>
                  <div className="mt-1 text-xs text-purple-600/70 dark:text-purple-400/70">
                    Driven by agent conversation
                  </div>
                </div>

                {/* Recommendation Acceptance */}
                <div className="rounded-xl border border-purple-100 bg-purple-50/40 p-5 shadow-sm dark:border-purple-900/30 dark:bg-purple-950/20">
                  <div className="text-xs font-medium text-purple-700 dark:text-purple-300">Recommendation Rate</div>
                  <div className="mt-2 text-2xl font-bold tracking-tight text-purple-700 dark:text-purple-300">
                    {loading ? "—" : `${metrics?.recommendation_acceptance_rate || 0}%`}
                  </div>
                  <div className="mt-1 text-xs text-purple-600/70 dark:text-purple-400/70">
                    {metrics?.recommendations_accepted || 0} / {metrics?.recommendations_generated || 0} accepted
                  </div>
                </div>

                {/* Upsell & Cross-Sell Revenue */}
                <div className="rounded-xl border border-purple-100 bg-purple-50/40 p-5 shadow-sm dark:border-purple-900/30 dark:bg-purple-950/20">
                  <div className="text-xs font-medium text-purple-700 dark:text-purple-300">Incremental Growth</div>
                  <div className="mt-2 text-2xl font-bold tracking-tight text-purple-700 dark:text-purple-300">
                    {loading
                      ? "—"
                      : formatCurrency(
                          Number(metrics?.upsell_revenue || 0) + Number(metrics?.cross_sell_revenue || 0)
                        )}
                  </div>
                  <div className="mt-1 text-xs text-purple-600/70 dark:text-purple-400/70">
                    {metrics?.upsell_count || 0} upsell(s), {metrics?.cross_sell_count || 0} cross-sell(s)
                  </div>
                </div>
              </div>
            </section>

            {/* Section 3: Recent Orders Table */}
            <section className="rounded-xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900 overflow-hidden">
              <div className="px-6 py-4 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">Recent Customer Orders</h2>
                  <p className="text-xs text-zinc-500 dark:text-zinc-400">Chronological list of order conversions</p>
                </div>
                <span className="text-xs text-zinc-400">{orders.length} order(s) loaded</span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-50/50 text-zinc-500 dark:bg-zinc-800/50 dark:text-zinc-400 border-b border-zinc-100 dark:border-zinc-800">
                    <tr>
                      <th className="px-6 py-3 font-medium">Order ID</th>
                      <th className="px-6 py-3 font-medium">Total</th>
                      <th className="px-6 py-3 font-medium">Status</th>
                      <th className="px-6 py-3 font-medium">Payment</th>
                      <th className="px-6 py-3 font-medium">AI Attributed</th>
                      <th className="px-6 py-3 font-medium">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
                    {loading ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-zinc-400">
                          Loading orders...
                        </td>
                      </tr>
                    ) : orders.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-zinc-400">
                          No orders recorded yet. Initiate a checkout flow to see live data.
                        </td>
                      </tr>
                    ) : (
                      orders.map((order) => (
                        <tr key={order.id} className="hover:bg-zinc-50/60 dark:hover:bg-zinc-800/40">
                          <td className="px-6 py-3.5 font-mono text-[11px] text-zinc-600 dark:text-zinc-300">
                            {order.id.slice(0, 8)}...
                          </td>
                          <td className="px-6 py-3.5 font-semibold">
                            {formatCurrency(order.total)}
                          </td>
                          <td className="px-6 py-3.5">
                            <span
                              className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                order.status === "completed"
                                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                                  : order.status === "pending"
                                  ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300"
                                  : "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
                              }`}
                            >
                              {order.status}
                            </span>
                          </td>
                          <td className="px-6 py-3.5">
                            <span
                              className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                                order.payment_status === "paid"
                                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                                  : "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400"
                              }`}
                            >
                              {order.payment_status || "unpaid"}
                            </span>
                          </td>
                          <td className="px-6 py-3.5">
                            {order.is_ai_assisted ? (
                              <span className="inline-flex items-center gap-1 text-[11px] text-purple-600 dark:text-purple-400 font-medium">
                                <span>✨</span> AI Assisted
                              </span>
                            ) : (
                              <span className="text-[11px] text-zinc-400">Direct</span>
                            )}
                          </td>
                          <td className="px-6 py-3.5 text-zinc-400">
                            {formatDate(order.created_at)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            {/* Section 4: Audit Activity Feed */}
            <section className="rounded-xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-900 p-6">
              <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-1">
                Live Audit Trail Activity Feed
              </h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-4">
                Real-time security-sanitized log of customer interactions and agent recommendations
              </p>

              <div className="space-y-3">
                {loading ? (
                  <p className="text-xs text-zinc-400 py-4 text-center">Loading audit events...</p>
                ) : activities.length === 0 ? (
                  <p className="text-xs text-zinc-400 py-4 text-center">
                    No recent audit events. Use the AI search or cart on the store page to generate events.
                  </p>
                ) : (
                  activities.map((act) => (
                    <div
                      key={act.id}
                      className="flex items-start justify-between rounded-lg bg-zinc-50/70 p-3 text-xs dark:bg-zinc-800/50"
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="text-sm">
                          {act.event_type.includes("PAYMENT")
                            ? "💳"
                            : act.event_type.includes("CART")
                            ? "🛒"
                            : act.event_type.includes("RECOMMEND")
                            ? "✨"
                            : act.event_type.includes("ORDER")
                            ? "📦"
                            : "🤖"}
                        </span>
                        <div>
                          <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                            {act.event_type}
                          </span>
                          {act.action && (
                            <span className="ml-2 text-[11px] text-zinc-500 dark:text-zinc-400">
                              ({act.action})
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${
                            act.status === "success"
                              ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300"
                              : "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300"
                          }`}
                        >
                          {act.status}
                        </span>
                        <span className="text-[11px] text-zinc-400">{formatDate(act.created_at)}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
