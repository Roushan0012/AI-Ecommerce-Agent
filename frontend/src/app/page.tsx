"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  API_BASE_URL,
  HealthResponse,
  ProductItem,
  fetchCurrentUser,
  fetchHealth,
  fetchProducts,
  loginUser,
  logoutUser,
  registerUser,
} from "@/lib/api";
import { AuthUser, subscribeAuth } from "@/lib/auth";

const CATEGORIES = [
  "All",
  "Audio",
  "Computer Accessories",
  "Chargers & Cables",
  "Work & Travel",
];

const CATEGORY_ICONS: Record<string, string> = {
  All: "📦",
  Audio: "🎧",
  "Computer Accessories": "⌨️",
  "Chargers & Cables": "⚡",
  "Work & Travel": "🎒",
};

export default function Home() {
  // Backend health state
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);

  // Authentication state
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [emailInput, setEmailInput] = useState<string>("");
  const [passwordInput, setPasswordInput] = useState<string>("");
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);

  // Catalog state
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [totalProducts, setTotalProducts] = useState<number>(0);
  const [loadingProducts, setLoadingProducts] = useState<boolean>(true);
  const [productError, setProductError] = useState<string | null>(null);
  const [page, setPage] = useState<number>(1);
  const pageSize = 12;

  // Search and filter state
  const [searchInput, setSearchInput] = useState<string>("");
  const [activeSearch, setActiveSearch] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");

  // Add to Cart placeholder feedback
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const formatCurrency = (amount: string | number) => {
    const num = Number(amount || 0);
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 2,
    }).format(num);
  };

  // Load products from backend API
  const loadCatalog = useCallback(
    async (searchKw?: string, cat?: string, pageNum: number = 1) => {
      setLoadingProducts(true);
      setProductError(null);
      try {
        const data = await fetchProducts({
          search: searchKw?.trim() || undefined,
          category: cat && cat !== "All" ? cat : undefined,
          available: true,
          page: pageNum,
          page_size: pageSize,
        });
        setProducts(data.items || []);
        setTotalProducts(data.total || 0);
      } catch (err: unknown) {
        setProducts([]);
        setTotalProducts(0);
        setProductError(
          err instanceof Error
            ? err.message
            : "Failed to load products from server. Verify backend is running."
        );
      } finally {
        setLoadingProducts(false);
      }
    },
    [pageSize]
  );

  // Initialize connection & session
  useEffect(() => {
    let ignore = false;

    async function initialize() {
      // 1. Check backend health
      try {
        const h = await fetchHealth();
        if (!ignore) setHealth(h);
      } catch {
        if (!ignore) setHealth(null);
      } finally {
        if (!ignore) setHealthLoading(false);
      }

      // 2. Restore authenticated session
      const user = await fetchCurrentUser();
      if (!ignore) setCurrentUser(user);

      // 3. Load initial catalog
      if (!ignore) {
        await loadCatalog("", "All", 1);
      }
    }

    initialize();

    const unsubscribe = subscribeAuth((state) => {
      if (!ignore) {
        setCurrentUser(state.user);
      }
    });

    return () => {
      ignore = true;
      unsubscribe();
    };
  }, [loadCatalog]);

  // Search handler
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setActiveSearch(searchInput);
    setPage(1);
    loadCatalog(searchInput, selectedCategory, 1);
  };

  // Category filter handler
  const handleCategorySelect = (category: string) => {
    setSelectedCategory(category);
    setPage(1);
    loadCatalog(activeSearch, category, 1);
  };

  // Clear filters
  const handleClearFilters = () => {
    setSearchInput("");
    setActiveSearch("");
    setSelectedCategory("All");
    setPage(1);
    loadCatalog("", "All", 1);
  };

  // Pagination handlers
  const totalPages = Math.ceil(totalProducts / pageSize) || 1;

  const handlePrevPage = () => {
    if (page > 1) {
      const nextP = page - 1;
      setPage(nextP);
      loadCatalog(activeSearch, selectedCategory, nextP);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const handleNextPage = () => {
    if (page < totalPages) {
      const nextP = page + 1;
      setPage(nextP);
      loadCatalog(activeSearch, selectedCategory, nextP);
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  // Auth handlers
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
        setTimeout(() => setShowAuthModal(false), 800);
      } else {
        await registerUser(emailInput, passwordInput);
        setAuthSuccess("Account registered! Logging in...");
        const { user } = await loginUser(emailInput, passwordInput);
        setCurrentUser(user);
        setPasswordInput("");
        setTimeout(() => setShowAuthModal(false), 800);
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

  // Add to cart placeholder feedback
  const handleAddToCart = (product: ProductItem) => {
    setToastMessage(`"${product.name}" added to cart selection (Cart integration in Step 2)`);
    setTimeout(() => {
      setToastMessage(null);
    }, 3200);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-indigo-500 selection:text-white">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl border border-indigo-500/40 bg-zinc-900/95 px-4 py-3 text-xs font-medium text-indigo-300 shadow-2xl backdrop-blur-md animate-fade-in">
          <span>🛒</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Navigation Header */}
      <header className="sticky top-0 z-40 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-purple-600 text-white font-black text-sm shadow-md shadow-indigo-500/20 group-hover:scale-105 transition-transform">
                AI
              </div>
              <div>
                <span className="text-base font-bold tracking-tight text-white group-hover:text-indigo-300 transition-colors">
                  AI Commerce Store
                </span>
                <span className="hidden sm:inline-block ml-2 rounded-full border border-emerald-500/30 bg-emerald-950/40 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                  Track 01
                </span>
              </div>
            </Link>
          </div>

          <div className="flex items-center gap-3">
            {/* Backend Health Status Pill */}
            <div className="hidden md:flex items-center gap-2 rounded-full border border-zinc-800 bg-zinc-900/60 px-3 py-1 text-xs text-zinc-400 font-mono">
              <span
                className={`h-2 w-2 rounded-full ${
                  healthLoading
                    ? "bg-amber-400 animate-pulse"
                    : health
                    ? "bg-emerald-400"
                    : "bg-rose-400"
                }`}
              />
              <span className="text-[11px]">
                {healthLoading ? "Connecting..." : health ? "API Online" : "API Offline"}
              </span>
            </div>

            {/* Merchant Dashboard Link */}
            <Link
              href="/dashboard"
              className="rounded-lg border border-zinc-800 bg-zinc-900/80 px-3 py-1.5 text-xs font-semibold text-zinc-300 shadow-sm transition hover:border-zinc-700 hover:bg-zinc-800 hover:text-white"
            >
              📊 Merchant Dashboard
            </Link>

            {/* User Account Controls */}
            {currentUser ? (
              <div className="flex items-center gap-2">
                <div className="hidden sm:flex flex-col text-right">
                  <span className="text-xs font-semibold text-zinc-200">
                    {currentUser.email}
                  </span>
                  <span className="text-[10px] uppercase font-bold text-indigo-400">
                    {currentUser.role}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="rounded-lg border border-rose-900/40 bg-rose-950/30 px-2.5 py-1.5 text-xs font-medium text-rose-300 hover:bg-rose-900/50 transition cursor-pointer"
                >
                  Log Out
                </button>
              </div>
            ) : (
              <button
                onClick={() => {
                  setShowAuthModal(true);
                  setAuthError(null);
                  setAuthSuccess(null);
                }}
                className="rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm shadow-indigo-600/30 hover:bg-indigo-500 transition cursor-pointer"
              >
                Sign In
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-8">
        {/* Storefront Hero Banner */}
        <section className="relative overflow-hidden rounded-2xl border border-zinc-800/80 bg-gradient-to-b from-zinc-900 via-zinc-900/60 to-zinc-950 p-6 sm:p-10 shadow-xl">
          <div className="relative z-10 max-w-3xl space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-950/40 px-3 py-1 text-xs font-medium text-indigo-300 backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
              Verified Catalog & Real-Time Stock
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl lg:text-5xl">
              Next-Gen Electronics & Smart Workspace Gear
            </h1>
            <p className="text-sm leading-relaxed text-zinc-400 sm:text-base">
              Discover audio gear, ergonomic mechanical keyboards, high-speed power hubs, and travel tech powered by real-time inventory and Razorpay checkout.
            </p>

            {/* Search Input Form */}
            <form onSubmit={handleSearchSubmit} className="pt-2 flex flex-col sm:flex-row gap-2.5">
              <div className="relative flex-1">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-zinc-500">
                  🔍
                </span>
                <input
                  type="text"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search products by keyword (e.g. headphones, keyboard, usb-c, organizer)..."
                  className="w-full rounded-xl border border-zinc-800 bg-zinc-950/90 pl-10 pr-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none transition-all shadow-inner"
                />
                {searchInput && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchInput("");
                      if (activeSearch) {
                        setActiveSearch("");
                        setPage(1);
                        loadCatalog("", selectedCategory, 1);
                      }
                    }}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-xs text-zinc-500 hover:text-zinc-300"
                  >
                    Clear
                  </button>
                )}
              </div>
              <button
                type="submit"
                disabled={loadingProducts}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50 transition cursor-pointer"
              >
                {loadingProducts ? "Searching..." : "Search"}
              </button>
            </form>
          </div>

          <div className="absolute -right-16 -top-16 h-72 w-72 rounded-full bg-indigo-600/10 blur-3xl pointer-events-none" />
          <div className="absolute -left-16 -bottom-16 h-72 w-72 rounded-full bg-purple-600/10 blur-3xl pointer-events-none" />
        </section>

        {/* Category Pills Filter & Results Count Bar */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-4">
            {/* Category Filter Pills */}
            <div className="flex flex-wrap items-center gap-2">
              {CATEGORIES.map((category) => {
                const isSelected = selectedCategory === category;
                return (
                  <button
                    key={category}
                    onClick={() => handleCategorySelect(category)}
                    className={`inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
                      isSelected
                        ? "bg-white text-zinc-950 shadow-md scale-105"
                        : "border border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                    }`}
                  >
                    <span>{CATEGORY_ICONS[category] || "🏷️"}</span>
                    <span>{category}</span>
                  </button>
                );
              })}
            </div>

            {/* Results Count & Active Filter Indicator */}
            <div className="flex items-center gap-2 text-xs text-zinc-400">
              <span>
                {loadingProducts
                  ? "Loading products..."
                  : `Showing ${products.length} of ${totalProducts} product(s)`}
              </span>
              {(activeSearch || selectedCategory !== "All") && (
                <button
                  onClick={handleClearFilters}
                  className="text-xs font-semibold text-indigo-400 hover:underline cursor-pointer"
                >
                  Reset all filters
                </button>
              )}
            </div>
          </div>
        </section>

        {/* Error State */}
        {productError && (
          <div className="rounded-2xl border border-rose-900/50 bg-rose-950/30 p-6 text-center space-y-3">
            <div className="text-2xl">⚠️</div>
            <h3 className="text-base font-bold text-rose-300">
              Unable to load catalog products
            </h3>
            <p className="text-xs text-rose-400 max-w-md mx-auto">
              {productError}
            </p>
            <button
              onClick={() => loadCatalog(activeSearch, selectedCategory, page)}
              className="rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-500 transition cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading Skeleton Grid */}
        {loadingProducts && !productError && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {Array.from({ length: 8 }).map((_, idx) => (
              <div
                key={idx}
                className="flex flex-col justify-between rounded-2xl border border-zinc-800/60 bg-zinc-900/40 p-5 space-y-4 animate-pulse"
              >
                <div className="space-y-2.5">
                  <div className="h-4 w-24 bg-zinc-800 rounded" />
                  <div className="h-5 w-3/4 bg-zinc-800 rounded" />
                  <div className="h-12 w-full bg-zinc-800/60 rounded" />
                </div>
                <div className="pt-4 border-t border-zinc-800/60 flex items-center justify-between">
                  <div className="h-6 w-20 bg-zinc-800 rounded" />
                  <div className="h-8 w-24 bg-zinc-800 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loadingProducts && !productError && products.length === 0 && (
          <div className="rounded-2xl border border-zinc-800/80 bg-zinc-900/30 p-12 text-center space-y-4">
            <div className="text-4xl">🔍</div>
            <h3 className="text-lg font-bold text-white">No products found</h3>
            <p className="text-xs text-zinc-400 max-w-md mx-auto">
              {activeSearch
                ? `No products matched "${activeSearch}" in category "${selectedCategory}".`
                : `There are currently no active products in category "${selectedCategory}".`}
            </p>
            <button
              onClick={handleClearFilters}
              className="rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-2 text-xs font-semibold text-zinc-200 hover:bg-zinc-700 hover:text-white transition cursor-pointer"
            >
              Clear filters & view all products
            </button>
          </div>
        )}

        {/* Product Cards Grid */}
        {!loadingProducts && !productError && products.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {products.map((product) => {
              const inStock = product.inventory > 0;
              return (
                <div
                  key={product.id}
                  className="group relative flex flex-col justify-between rounded-2xl border border-zinc-800/80 bg-zinc-900/60 p-5 shadow-md transition-all hover:border-zinc-700 hover:bg-zinc-900 hover:shadow-xl hover:shadow-indigo-500/5"
                >
                  <div className="space-y-3">
                    {/* Category & Stock Badges */}
                    <div className="flex items-center justify-between gap-2">
                      <span className="inline-flex items-center gap-1 rounded-md bg-zinc-800 px-2 py-0.5 text-[11px] font-medium text-zinc-300">
                        <span>{CATEGORY_ICONS[product.category || ""] || "🏷️"}</span>
                        <span>{product.category || "General"}</span>
                      </span>

                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                          inStock
                            ? "bg-emerald-950/60 text-emerald-400 border border-emerald-900/50"
                            : "bg-rose-950/60 text-rose-400 border border-rose-900/50"
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            inStock ? "bg-emerald-400" : "bg-rose-400"
                          }`}
                        />
                        <span>{inStock ? `${product.inventory} in stock` : "Out of stock"}</span>
                      </span>
                    </div>

                    {/* Product Name & SKU */}
                    <div>
                      <h3 className="text-sm font-bold text-white group-hover:text-indigo-300 transition-colors line-clamp-2">
                        {product.name}
                      </h3>
                      <p className="text-[10px] font-mono text-zinc-500 mt-0.5">
                        SKU: {product.sku}
                      </p>
                    </div>

                    {/* Product Description */}
                    <p className="text-xs text-zinc-400 line-clamp-3 leading-relaxed">
                      {product.description || "No description provided."}
                    </p>
                  </div>

                  {/* Price & Action Button Footer */}
                  <div className="mt-5 pt-4 border-t border-zinc-800/80 flex items-center justify-between gap-3">
                    <div>
                      <span className="text-[10px] uppercase font-semibold text-zinc-500 block">
                        Price
                      </span>
                      <span className="text-base font-extrabold text-white tracking-tight">
                        {formatCurrency(product.price)}
                      </span>
                    </div>

                    <button
                      onClick={() => handleAddToCart(product)}
                      disabled={!inStock}
                      className={`inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-xs font-semibold shadow-sm transition-all cursor-pointer ${
                        inStock
                          ? "bg-indigo-600 text-white shadow-indigo-600/20 hover:bg-indigo-500 hover:scale-102 active:scale-98"
                          : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                      }`}
                    >
                      <span>🛒</span>
                      <span>{inStock ? "Add to Cart" : "Sold Out"}</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination Controls */}
        {!loadingProducts && !productError && totalPages > 1 && (
          <div className="flex items-center justify-center gap-4 pt-6 border-t border-zinc-800/60">
            <button
              onClick={handlePrevPage}
              disabled={page <= 1}
              className="rounded-lg border border-zinc-800 bg-zinc-900 px-3.5 py-2 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
            >
              ← Previous
            </button>
            <span className="text-xs text-zinc-400">
              Page <strong className="text-white">{page}</strong> of{" "}
              <strong className="text-white">{totalPages}</strong>
            </span>
            <button
              onClick={handleNextPage}
              disabled={page >= totalPages}
              className="rounded-lg border border-zinc-800 bg-zinc-900 px-3.5 py-2 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
            >
              Next →
            </button>
          </div>
        )}
      </main>

      {/* Customer / Merchant Authentication Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="relative w-full max-w-md rounded-2xl border border-zinc-800 bg-zinc-900 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode("login");
                    setAuthError(null);
                  }}
                  className={`text-sm font-bold pb-1 cursor-pointer ${
                    authMode === "login"
                      ? "text-white border-b-2 border-indigo-500"
                      : "text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  Sign In
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode("register");
                    setAuthError(null);
                  }}
                  className={`text-sm font-bold pb-1 cursor-pointer ${
                    authMode === "register"
                      ? "text-white border-b-2 border-indigo-500"
                      : "text-zinc-500 hover:text-zinc-300"
                  }`}
                >
                  Create Account
                </button>
              </div>

              <button
                onClick={() => setShowAuthModal(false)}
                className="text-zinc-500 hover:text-zinc-300 text-sm font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleAuthSubmit} className="space-y-3.5 pt-2">
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  placeholder="customer@example.com"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  required
                  placeholder="Password (min 8 chars)"
                  value={passwordInput}
                  onChange={(e) => setPasswordInput(e.target.value)}
                  className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3.5 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:border-indigo-500 focus:outline-none"
                />
              </div>

              {authError && (
                <div className="rounded-lg bg-rose-950/50 border border-rose-900/50 p-2.5 text-xs text-rose-300">
                  {authError}
                </div>
              )}

              {authSuccess && (
                <div className="rounded-lg bg-emerald-950/50 border border-emerald-900/50 p-2.5 text-xs text-emerald-300">
                  {authSuccess}
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  disabled={authLoading}
                  className="flex-1 rounded-xl bg-indigo-600 py-2.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition cursor-pointer"
                >
                  {authLoading
                    ? "Authenticating..."
                    : authMode === "login"
                    ? "Sign In with JWT"
                    : "Create Customer Account"}
                </button>
                <button
                  type="button"
                  onClick={fillDemoMerchant}
                  className="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-xs font-semibold text-zinc-400 hover:text-zinc-200 transition cursor-pointer"
                >
                  Demo Merchant
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Storefront Footer */}
      <footer className="border-t border-zinc-900 mt-20 py-8 text-center text-xs text-zinc-500 space-y-2">
        <div className="flex justify-center items-center gap-4">
          <Link href="/dashboard" className="text-zinc-400 hover:text-zinc-200 transition">
            Merchant Dashboard
          </Link>
          <span>•</span>
          <span className="font-mono text-zinc-600">FastAPI Backend ({API_BASE_URL})</span>
          <span>•</span>
          <span className="font-mono text-zinc-600">Track 01</span>
        </div>
        <p>© 2026 AI Commerce Agent Platform. All prices and inventory are backend-authoritative.</p>
      </footer>
    </div>
  );
}
