"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  DashboardActivityItem,
  DashboardOrderItem,
  OverviewMetricsResponse,
  fetchDashboardActivity,
  fetchDashboardOrders,
  fetchDashboardOverview,
} from "@/lib/api";

export default function MerchantDashboard() {
  const [metrics, setMetrics] = useState<OverviewMetricsResponse | null>(null);
  const [orders, setOrders] = useState<DashboardOrderItem[]>([]);
  const [activities, setActivities] = useState<DashboardActivityItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

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
    loadDashboardData();
  }, [loadDashboardData]);

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
            {lastUpdated && (
              <span className="text-xs text-zinc-400 dark:text-zinc-500">
                Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={loadDashboardData}
              disabled={loading}
              className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 shadow-sm transition hover:bg-zinc-50 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700 cursor-pointer"
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
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
              <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Average Order Value (AOV)</div>
              <div className="mt-2 text-2xl font-bold tracking-tight">
                {loading ? "—" : formatCurrency(metrics?.average_order_value)}
              </div>
              <div className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                Revenue / completed orders
              </div>
            </div>
          </div>
        </section>

        {/* Section 2: AI Commerce & Growth Engine Metrics */}
        <section>
          <h2 className="text-xs font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-4">
            AI Agent & Growth Performance
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {/* AI-Assisted Orders */}
            <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">AI-Assisted Orders</div>
              <div className="mt-2 text-2xl font-bold tracking-tight text-violet-600 dark:text-violet-400">
                {loading ? "—" : metrics?.ai_assisted_orders_count || 0}
              </div>
              <div className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                {metrics?.ai_assisted_percentage || 0}% of completed orders ({formatCurrency(metrics?.ai_assisted_revenue)})
              </div>
            </div>

            {/* Recommendation Acceptance */}
            <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Recommendation Acceptance</div>
              <div className="mt-2 text-2xl font-bold tracking-tight text-sky-600 dark:text-sky-400">
                {loading ? "—" : `${metrics?.recommendation_acceptance_rate || 0}%`}
              </div>
              <div className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                {metrics?.recommendations_accepted || 0} converted / {metrics?.recommendations_generated || 0} generated
              </div>
            </div>

            {/* Upsell Revenue */}
            <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Upsell Revenue</div>
              <div className="mt-2 text-2xl font-bold tracking-tight text-amber-600 dark:text-amber-400">
                {loading ? "—" : formatCurrency(metrics?.upsell_revenue)}
              </div>
              <div className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                {metrics?.upsell_count || 0} tier upgrades accepted
              </div>
            </div>

            {/* Cross-sell Revenue */}
            <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
              <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400">Cross-sell Revenue</div>
              <div className="mt-2 text-2xl font-bold tracking-tight text-teal-600 dark:text-teal-400">
                {loading ? "—" : formatCurrency(metrics?.cross_sell_revenue)}
              </div>
              <div className="mt-1 text-xs text-zinc-400 dark:text-zinc-500">
                {metrics?.cross_sell_count || 0} companion accessories added
              </div>
            </div>
          </div>
        </section>

        {/* Section 3: Dual Grid for Recent Orders and Agent Activity */}
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          {/* Recent Orders Table */}
          <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                Recent Orders
              </h3>
              <span className="text-xs text-zinc-400 dark:text-zinc-500">
                {orders.length} order(s)
              </span>
            </div>

            {loading ? (
              <div className="py-8 text-center text-xs text-zinc-400">Loading orders...</div>
            ) : orders.length === 0 ? (
              <div className="py-8 text-center text-xs text-zinc-400">No recent orders found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-zinc-100 text-zinc-400 dark:border-zinc-800">
                      <th className="pb-2 font-medium">Order ID</th>
                      <th className="pb-2 font-medium">Amount</th>
                      <th className="pb-2 font-medium">Status</th>
                      <th className="pb-2 font-medium">Channel</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800/60">
                    {orders.map((o) => (
                      <tr key={o.id} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-800/30">
                        <td className="py-2.5 font-mono text-[11px] text-zinc-600 dark:text-zinc-300">
                          {o.id.slice(0, 8)}...
                        </td>
                        <td className="py-2.5 font-semibold text-zinc-900 dark:text-zinc-100">
                          {formatCurrency(o.total)}
                        </td>
                        <td className="py-2.5">
                          <span
                            className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                              o.status === "paid"
                                ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400"
                                : o.status === "cancelled"
                                ? "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400"
                                : "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400"
                            }`}
                          >
                            {o.status}
                          </span>
                        </td>
                        <td className="py-2.5">
                          {o.is_ai_assisted ? (
                            <span className="inline-flex items-center gap-1 rounded bg-violet-100 px-1.5 py-0.5 text-[10px] font-medium text-violet-800 dark:bg-violet-950/60 dark:text-violet-300">
                              <span>🤖</span> AI Assisted
                            </span>
                          ) : (
                            <span className="text-zinc-400 text-[10px]">Direct</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Recent Agent Activity Feed */}
          <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
                Agent & Commerce Audit Activity
              </h3>
              <span className="text-xs text-zinc-400 dark:text-zinc-500">
                {activities.length} event(s)
              </span>
            </div>

            {loading ? (
              <div className="py-8 text-center text-xs text-zinc-400">Loading audit events...</div>
            ) : activities.length === 0 ? (
              <div className="py-8 text-center text-xs text-zinc-400">No agent activities logged.</div>
            ) : (
              <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
                {activities.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-center justify-between rounded-lg border border-zinc-100 bg-zinc-50/60 p-2.5 text-xs dark:border-zinc-800 dark:bg-zinc-800/40"
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-zinc-800 dark:text-zinc-200">
                          {a.event_type}
                        </span>
                        {a.action && (
                          <span className="font-mono text-[10px] text-zinc-500 dark:text-zinc-400">
                            ({a.action})
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-zinc-400 dark:text-zinc-500">
                        {formatDate(a.created_at)}
                      </div>
                    </div>

                    <div>
                      <span
                        className={`inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                          a.status === "success"
                            ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-400"
                            : a.status === "rejected"
                            ? "bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-400"
                            : "bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-400"
                        }`}
                      >
                        {a.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
