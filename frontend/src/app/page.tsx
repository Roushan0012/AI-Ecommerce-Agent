"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  API_BASE_URL,
  AgentSearchResponse,
  CartResponse,
  HealthResponse,
  ProductItem,
  addToCart,
  fetchCart,
  fetchCurrentUser,
  fetchHealth,
  fetchProductById,
  fetchProducts,
  loginUser,
  logoutUser,
  registerUser,
  searchWithAgent,
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

const AI_EXAMPLE_PROMPTS = [
  "I need wireless headphones",
  "mechanical keyboard",
  "fast charger",
  "travel organizer",
];

function formatCurrency(amount: string | number): string {
  const num = Number(amount || 0);
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(num);
}

interface ProductCardProps {
  product: ProductItem;
  onAddToCart: (product: ProductItem) => void;
  onOpenDetails: (productId: string) => void;
  isAdding?: boolean;
  isAiMatch?: boolean;
}

function ProductCard({
  product,
  onAddToCart,
  onOpenDetails,
  isAdding,
  isAiMatch,
}: ProductCardProps) {
  const inStock = product.inventory > 0;

  return (
    <div className="group relative flex flex-col justify-between rounded-2xl border border-zinc-800/80 bg-zinc-900/60 p-5 shadow-md transition-all hover:border-zinc-700 hover:bg-zinc-900 hover:shadow-xl hover:shadow-indigo-500/5">
      <div className="space-y-3">
        {/* Category & Stock Badges */}
        <div className="flex items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1 rounded-md bg-zinc-800 px-2 py-0.5 text-[11px] font-medium text-zinc-300">
            <span>{CATEGORY_ICONS[product.category || ""] || "🏷️"}</span>
            <span>{product.category || "General"}</span>
          </span>

          <div className="flex items-center gap-1.5">
            {isAiMatch && (
              <span className="inline-flex items-center gap-1 rounded-full bg-purple-950/70 border border-purple-800/60 px-2 py-0.5 text-[10px] font-semibold text-purple-300">
                ✨ AI Match
              </span>
            )}
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
        </div>

        {/* Product Name (Clickable to open Product Details) & SKU */}
        <div>
          <button
            type="button"
            onClick={() => onOpenDetails(product.id)}
            className="text-left text-sm font-bold text-white group-hover:text-indigo-300 transition-colors line-clamp-2 cursor-pointer w-full"
            aria-label={`View details for ${product.name}`}
          >
            {product.name}
          </button>
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
      <div className="mt-5 pt-4 border-t border-zinc-800/80 space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-[10px] uppercase font-semibold text-zinc-500 block">
              Price
            </span>
            <span className="text-base font-extrabold text-white tracking-tight">
              {formatCurrency(product.price)}
            </span>
          </div>

          <span className="text-[11px] font-mono text-zinc-400">
            {inStock ? `${product.inventory} available` : "Unavailable"}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            data-testid="view-details-btn"
            onClick={() => onOpenDetails(product.id)}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-zinc-700 bg-zinc-800/90 py-2.5 px-3 text-xs font-semibold text-zinc-200 hover:bg-zinc-700 hover:text-white hover:border-zinc-500 transition cursor-pointer shadow-sm"
            aria-label={`View details for ${product.name}`}
          >
            <span>👁️</span>
            <span>View Details</span>
          </button>

          <button
            type="button"
            data-testid="add-to-cart-btn"
            onClick={() => onAddToCart(product)}
            disabled={!inStock || isAdding}
            className={`inline-flex items-center justify-center gap-1.5 rounded-xl py-2.5 px-3 text-xs font-semibold shadow-sm transition-all cursor-pointer ${
              inStock
                ? "bg-indigo-600 text-white shadow-indigo-600/20 hover:bg-indigo-500 hover:scale-101 active:scale-99 disabled:opacity-50"
                : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
            }`}
          >
            <span>{isAdding ? "⏳" : "🛒"}</span>
            <span>
              {isAdding
                ? "Adding..."
                : inStock
                ? "Add to Cart"
                : "Sold Out"}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  // Backend health state
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthLoading, setHealthLoading] = useState<boolean>(true);

  // Authentication state
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [showAuthModal, setShowAuthModal] = useState<boolean>(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authPromptReason, setAuthPromptReason] = useState<string | null>(null);
  const [emailInput, setEmailInput] = useState<string>("");
  const [passwordInput, setPasswordInput] = useState<string>("");
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [authSuccess, setAuthSuccess] = useState<string | null>(null);

  // Step 1: Catalog & direct search state
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [totalProducts, setTotalProducts] = useState<number>(0);
  const [loadingProducts, setLoadingProducts] = useState<boolean>(true);
  const [productError, setProductError] = useState<string | null>(null);
  const [page, setPage] = useState<number>(1);
  const pageSize = 12;
  const [searchInput, setSearchInput] = useState<string>("");
  const [activeSearch, setActiveSearch] = useState<string>("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");

  // Step 2: AI Shopping Assistant state
  const [aiPrompt, setAiPrompt] = useState<string>("");
  const [aiLoading, setAiLoading] = useState<boolean>(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiValidationError, setAiValidationError] = useState<string | null>(null);
  const [aiResponse, setAiResponse] = useState<AgentSearchResponse | null>(null);

  // Step 3A: Cart mutation state
  const [activeCart, setActiveCart] = useState<CartResponse | null>(null);
  const [cartItemCount, setCartItemCount] = useState<number>(0);
  const [addingProductId, setAddingProductId] = useState<string | null>(null);

  // Product Detail Modal state
  const [isDetailModalOpen, setIsDetailModalOpen] = useState<boolean>(false);
  const [detailProductId, setDetailProductId] = useState<string | null>(null);
  const [detailProduct, setDetailProduct] = useState<ProductItem | null>(null);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Toast notification state
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [toastType, setToastType] = useState<"success" | "error" | "info">("info");

  const showToast = (message: string, type: "success" | "error" | "info" = "info") => {
    setToastMessage(message);
    setToastType(type);
    setTimeout(() => {
      setToastMessage(null);
    }, 3500);
  };

  // Close Product Details modal with Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isDetailModalOpen) {
        handleCloseProductDetail();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isDetailModalOpen]);

  // Open Product Detail modal and fetch authoritative product details
  const handleOpenProductDetail = async (productId: string) => {
    setIsDetailModalOpen(true);
    setDetailProductId(productId);
    setDetailLoading(true);
    setDetailError(null);
    setDetailProduct(null);

    try {
      const data = await fetchProductById(productId);
      setDetailProduct(data);
    } catch (err: unknown) {
      setDetailError(
        err instanceof Error
          ? err.message
          : "Failed to load product details from server."
      );
    } finally {
      setDetailLoading(false);
    }
  };

  // Close Product Detail modal
  const handleCloseProductDetail = () => {
    setIsDetailModalOpen(false);
    setDetailProductId(null);
    setDetailProduct(null);
    setDetailError(null);
    setDetailLoading(false);
  };

  // Synchronize authenticated customer cart
  const syncCart = useCallback(async (customerId: string) => {
    try {
      const cart = await fetchCart(customerId);
      setActiveCart(cart);
      setCartItemCount(cart.item_count || 0);
    } catch {
      // Cart will be auto-created on first item add
    }
  }, []);

  // Load catalog from backend
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

  // Initialize session, health & catalog
  useEffect(() => {
    let ignore = false;

    async function initialize() {
      try {
        const h = await fetchHealth();
        if (!ignore) setHealth(h);
      } catch {
        if (!ignore) setHealth(null);
      } finally {
        if (!ignore) setHealthLoading(false);
      }

      const user = await fetchCurrentUser();
      if (!ignore) {
        setCurrentUser(user);
        if (user) {
          syncCart(user.id);
        }
      }

      if (!ignore) {
        await loadCatalog("", "All", 1);
      }
    }

    initialize();

    const unsubscribe = subscribeAuth((state) => {
      if (!ignore) {
        setCurrentUser(state.user);
        if (state.user) {
          syncCart(state.user.id);
        } else {
          setActiveCart(null);
          setCartItemCount(0);
        }
      }
    });

    return () => {
      ignore = true;
      unsubscribe();
    };
  }, [loadCatalog, syncCart]);

  // Direct catalog search handler
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

  // Clear catalog filters
  const handleClearFilters = () => {
    setSearchInput("");
    setActiveSearch("");
    setSelectedCategory("All");
    setPage(1);
    loadCatalog("", "All", 1);
  };

  // Step 2: AI Shopping Assistant search handler
  const handleAiSearch = async (promptToUse?: string) => {
    const rawQuery = promptToUse !== undefined ? promptToUse : aiPrompt;
    const query = rawQuery ? rawQuery.trim() : "";

    if (!query) {
      setAiValidationError("Please enter a shopping query or select an example prompt.");
      return;
    }

    setAiValidationError(null);
    setAiLoading(true);
    setAiError(null);
    setAiPrompt(query);

    try {
      const res = await searchWithAgent({
        message: query,
        page: 1,
        page_size: 10,
      });
      setAiResponse(res);
    } catch (err: unknown) {
      setAiError(
        err instanceof Error
          ? err.message
          : "Failed to process request with AI Shopping Agent. Please try again."
      );
      setAiResponse(null);
    } finally {
      setAiLoading(false);
    }
  };

  const handleClearAiSearch = () => {
    setAiPrompt("");
    setAiResponse(null);
    setAiError(null);
    setAiValidationError(null);
  };

  // Step 3A: Real authenticated Add to Cart mutation (Reused in card and detail modal)
  const handleAddToCart = async (product: ProductItem) => {
    // 1. Client-side stock check
    if (product.inventory <= 0) {
      showToast(`"${product.name}" is currently out of stock.`, "error");
      return;
    }

    // 2. Unauthenticated check -> Direct to Sign In
    if (!currentUser) {
      setAuthPromptReason("Please sign in or create an account to add items to your cart.");
      setShowAuthModal(true);
      return;
    }

    // 3. Authenticated cart mutation
    setAddingProductId(product.id);

    try {
      const updatedCart = await addToCart(currentUser.id, product.id, 1);
      setActiveCart(updatedCart);
      setCartItemCount(updatedCart.item_count);
      showToast(
        `Added "${product.name}" to cart! (Cart total: ${formatCurrency(updatedCart.total)})`,
        "success"
      );
    } catch (err: unknown) {
      const errorMsg =
        err instanceof Error
          ? err.message
          : "Failed to add item to cart. Please try again.";
      showToast(`Cart Error: ${errorMsg}`, "error");
    } finally {
      setAddingProductId(null);
    }
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
        syncCart(user.id);
        setAuthSuccess(`Welcome back, ${user.email}!`);
        setPasswordInput("");
        setTimeout(() => {
          setShowAuthModal(false);
          setAuthPromptReason(null);
        }, 800);
      } else {
        await registerUser(emailInput, passwordInput);
        setAuthSuccess("Account registered! Logging in...");
        const { user } = await loginUser(emailInput, passwordInput);
        setCurrentUser(user);
        syncCart(user.id);
        setPasswordInput("");
        setTimeout(() => {
          setShowAuthModal(false);
          setAuthPromptReason(null);
        }, 800);
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
    setActiveCart(null);
    setCartItemCount(0);
    setAuthSuccess(null);
    setAuthError(null);
  };

  const fillDemoCustomer = () => {
    setEmailInput("testcustomer@example.com");
    setPasswordInput("CustomerPassword123!");
    setAuthMode("login");
    setAuthError(null);
  };

  const fillDemoMerchant = () => {
    setEmailInput("merchant@example.com");
    setPasswordInput("MerchantPassword123!");
    setAuthMode("login");
    setAuthError(null);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 selection:bg-indigo-500 selection:text-white">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-xl border px-4 py-3 text-xs font-medium shadow-2xl backdrop-blur-md animate-fade-in ${
            toastType === "success"
              ? "border-emerald-500/40 bg-zinc-900/95 text-emerald-300"
              : toastType === "error"
              ? "border-rose-500/40 bg-zinc-900/95 text-rose-300"
              : "border-indigo-500/40 bg-zinc-900/95 text-indigo-300"
          }`}
        >
          <span>{toastType === "success" ? "✅" : toastType === "error" ? "⚠️" : "🛒"}</span>
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

            {/* Authenticated Cart Status Pill */}
            {currentUser && cartItemCount > 0 && (
              <div className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-500/40 bg-indigo-950/50 px-3 py-1.5 text-xs font-semibold text-indigo-300 shadow-sm">
                <span>🛒</span>
                <span>
                  {cartItemCount} item{cartItemCount > 1 ? "s" : ""}
                </span>
                {activeCart && (
                  <span className="font-mono text-white text-[11px]">
                    ({formatCurrency(activeCart.total)})
                  </span>
                )}
              </div>
            )}

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
                  type="button"
                  onClick={handleLogout}
                  className="rounded-lg border border-rose-900/40 bg-rose-950/30 px-2.5 py-1.5 text-xs font-medium text-rose-300 hover:bg-rose-900/50 transition cursor-pointer"
                >
                  Log Out
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => {
                  setAuthPromptReason(null);
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
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 space-y-12">
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
          </div>

          <div className="absolute -right-16 -top-16 h-72 w-72 rounded-full bg-indigo-600/10 blur-3xl pointer-events-none" />
          <div className="absolute -left-16 -bottom-16 h-72 w-72 rounded-full bg-purple-600/10 blur-3xl pointer-events-none" />
        </section>

        {/* STEP 2: AI Shopping Assistant Section */}
        <section className="relative overflow-hidden rounded-2xl border border-purple-500/30 bg-gradient-to-br from-purple-950/40 via-zinc-900/90 to-indigo-950/30 p-6 sm:p-8 shadow-xl shadow-purple-950/10 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-800/80 pb-4">
            <div className="space-y-1">
              <div className="inline-flex items-center gap-2 rounded-full border border-purple-500/40 bg-purple-950/50 px-3 py-0.5 text-xs font-semibold text-purple-300">
                <span className="h-1.5 w-1.5 rounded-full bg-purple-400 animate-pulse" />
                AI Commerce Agent • Natural Language
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2">
                <span>✨</span>
                <span>AI Shopping Assistant</span>
              </h2>
              <p className="text-xs sm:text-sm text-zinc-300 max-w-2xl">
                Describe your requirements in plain English (e.g. <em>"I need wireless headphones"</em>). The agent uses natural-language intent parsing to query the catalog.
              </p>
            </div>

            {aiResponse && (
              <button
                type="button"
                onClick={handleClearAiSearch}
                className="self-start sm:self-center text-xs font-semibold text-purple-400 hover:text-purple-300 transition cursor-pointer border border-purple-800/60 rounded-lg px-3 py-1.5 bg-purple-950/30"
              >
                ✕ Clear AI Search
              </button>
            )}
          </div>

          {/* AI Search Input Form */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleAiSearch();
            }}
            className="space-y-3"
          >
            <div>
              <label
                htmlFor="ai-natural-language-input"
                className="block text-xs font-semibold text-purple-300 mb-1.5"
              >
                Natural-Language Shopping Query:
              </label>
              <div className="flex flex-col sm:flex-row gap-2.5">
                <div className="relative flex-1">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3.5 pointer-events-none text-purple-400">
                    ✨
                  </span>
                  <input
                    id="ai-natural-language-input"
                    type="text"
                    value={aiPrompt}
                    onChange={(e) => {
                      setAiPrompt(e.target.value);
                      if (aiValidationError) setAiValidationError(null);
                    }}
                    placeholder="Ask AI: e.g. 'I need wireless headphones' or 'Ergonomic mechanical keyboard for typing'..."
                    className="w-full rounded-xl border border-purple-500/30 bg-zinc-950/90 pl-10 pr-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 focus:border-purple-400 focus:ring-1 focus:ring-purple-400 focus:outline-none transition-all shadow-inner"
                  />
                </div>
                <button
                  id="ask-ai-button"
                  type="submit"
                  disabled={aiLoading}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-purple-600/30 hover:from-purple-500 hover:to-indigo-500 disabled:opacity-50 transition cursor-pointer whitespace-nowrap"
                >
                  <span>{aiLoading ? "Thinking..." : "✨ Ask AI"}</span>
                </button>
              </div>
            </div>

            {/* Client-side input validation warning */}
            {aiValidationError && (
              <p className="text-xs font-medium text-amber-400 flex items-center gap-1.5">
                <span>⚠️</span>
                <span>{aiValidationError}</span>
              </p>
            )}

            {/* Interactive Example Prompts */}
            <div className="pt-1">
              <span className="text-[11px] font-semibold text-zinc-400 block mb-2">
                💡 Try an example query:
              </span>
              <div className="flex flex-wrap gap-2">
                {AI_EXAMPLE_PROMPTS.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => handleAiSearch(example)}
                    className="rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-1.5 text-xs text-zinc-300 hover:border-purple-500/50 hover:bg-purple-950/40 hover:text-purple-200 transition text-left cursor-pointer"
                  >
                    "{example}"
                  </button>
                ))}
              </div>
            </div>
          </form>

          {/* AI Loading State */}
          {aiLoading && (
            <div className="rounded-xl border border-purple-500/30 bg-purple-950/20 p-6 text-center space-y-3 animate-pulse">
              <div className="text-2xl animate-spin inline-block">✨</div>
              <h4 className="text-sm font-bold text-purple-200">
                AI Agent is analyzing your query...
              </h4>
              <p className="text-xs text-purple-400 max-w-md mx-auto">
                Extracting shopping intent, filtering catalog constraints, and evaluating stock in real-time.
              </p>
            </div>
          )}

          {/* AI Error State */}
          {aiError && !aiLoading && (
            <div className="rounded-xl border border-rose-900/50 bg-rose-950/30 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-rose-300 text-sm font-bold">
                  <span>⚠️</span>
                  <span>AI Agent Request Failed</span>
                </div>
                <button
                  type="button"
                  onClick={() => handleAiSearch()}
                  className="rounded-lg bg-rose-600 px-3 py-1 text-xs font-semibold text-white hover:bg-rose-500 transition cursor-pointer"
                >
                  Retry
                </button>
              </div>
              <p className="text-xs text-rose-400 leading-relaxed">{aiError}</p>
            </div>
          )}

          {/* AI Results & Insights */}
          {aiResponse && !aiLoading && (
            <div className="space-y-6 pt-2">
              {/* Agent Conversational Insight Box */}
              <div className="rounded-xl border border-purple-500/40 bg-zinc-950/80 p-4 sm:p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-purple-300 flex items-center gap-1.5">
                    <span>💬</span>
                    <span>AI Shopping Agent Response</span>
                  </span>
                  <span className="text-[11px] font-mono text-zinc-400">
                    Matches: <strong className="text-white">{aiResponse.total}</strong>
                  </span>
                </div>

                <p className="text-sm text-zinc-200 leading-relaxed font-medium">
                  {aiResponse.message}
                </p>

                {/* Extracted Intent Tags */}
                {aiResponse.intent && (
                  <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-zinc-800/80">
                    <span className="text-[11px] font-semibold text-zinc-500">
                      Parsed Intent:
                    </span>
                    {aiResponse.intent.search_query && (
                      <span className="rounded-md bg-purple-950/80 border border-purple-800/60 px-2 py-0.5 text-[10px] font-mono text-purple-300">
                        Query: {aiResponse.intent.search_query}
                      </span>
                    )}
                    {aiResponse.intent.category && (
                      <span className="rounded-md bg-indigo-950/80 border border-indigo-800/60 px-2 py-0.5 text-[10px] font-mono text-indigo-300">
                        Category: {aiResponse.intent.category}
                      </span>
                    )}
                    {aiResponse.intent.max_price && (
                      <span className="rounded-md bg-emerald-950/80 border border-emerald-800/60 px-2 py-0.5 text-[10px] font-mono text-emerald-300">
                        Max Budget: ₹{Number(aiResponse.intent.max_price).toLocaleString("en-IN")}
                      </span>
                    )}
                    {aiResponse.intent.min_price && (
                      <span className="rounded-md bg-emerald-950/80 border border-emerald-800/60 px-2 py-0.5 text-[10px] font-mono text-emerald-300">
                        Min Budget: ₹{Number(aiResponse.intent.min_price).toLocaleString("en-IN")}
                      </span>
                    )}
                  </div>
                )}
              </div>

              {/* Matched Product Cards */}
              {aiResponse.items.length > 0 ? (
                <div className="space-y-3">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-purple-300 flex items-center gap-2">
                    <span>✨</span>
                    <span>
                      AI Recommendations / AI Search Results ({aiResponse.items.length})
                    </span>
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                    {aiResponse.items.map((product) => (
                      <ProductCard
                        key={`ai-${product.id}`}
                        product={product}
                        onAddToCart={handleAddToCart}
                        onOpenDetails={handleOpenProductDetail}
                        isAdding={addingProductId === product.id}
                        isAiMatch
                      />
                    ))}
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-8 text-center space-y-2">
                  <p className="text-sm font-semibold text-zinc-300">
                    No products matched all AI constraints.
                  </p>
                  <p className="text-xs text-zinc-500">
                    Try broadening your search or adjusting price bounds.
                  </p>
                </div>
              )}
            </div>
          )}
        </section>

        {/* STEP 1: Direct Catalog & Search Section */}
        <section className="space-y-6 pt-4">
          <div className="border-b border-zinc-800/80 pb-4 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-1">
                <div className="inline-flex items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900 px-3 py-0.5 text-xs font-semibold text-zinc-300">
                  <span>📦</span>
                  <span>Direct Database Catalog • Keyword Search</span>
                </div>
                <h2 className="text-xl sm:text-2xl font-bold text-white">
                  Direct Catalog & Category Filter
                </h2>
                <p className="text-xs sm:text-sm text-zinc-400">
                  Search specific keywords directly or filter products by hardware category.
                </p>
              </div>

              {/* Direct Search Input Form */}
              <form onSubmit={handleSearchSubmit} className="flex gap-2">
                <div className="relative flex-1 sm:w-72">
                  <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-zinc-500 text-xs">
                    🔍
                  </span>
                  <input
                    id="catalog-keyword-search-input"
                    type="text"
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    placeholder="Keyword search (e.g. keyboard, cable)..."
                    className="w-full rounded-lg border border-zinc-800 bg-zinc-950 pl-8 pr-3 py-1.5 text-xs text-zinc-100 placeholder-zinc-500 focus:border-indigo-500 focus:outline-none"
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
                      className="absolute inset-y-0 right-0 flex items-center pr-2.5 text-[10px] text-zinc-500 hover:text-zinc-300"
                    >
                      ✕
                    </button>
                  )}
                </div>
                <button
                  id="direct-catalog-search-button"
                  type="submit"
                  disabled={loadingProducts}
                  className="rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 transition cursor-pointer whitespace-nowrap"
                >
                  Search Catalog
                </button>
              </form>
            </div>

            {/* Category Filter Pills & Results Count */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2">
              <div className="flex flex-wrap items-center gap-2">
                {CATEGORIES.map((category) => {
                  const isSelected = selectedCategory === category;
                  return (
                    <button
                      key={category}
                      type="button"
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

              <div className="flex items-center gap-2 text-xs text-zinc-400">
                <span>
                  {loadingProducts
                    ? "Loading catalog..."
                    : `Showing ${products.length} of ${totalProducts} catalog item(s)`}
                </span>
                {(activeSearch || selectedCategory !== "All") && (
                  <button
                    type="button"
                    onClick={handleClearFilters}
                    className="text-xs font-semibold text-indigo-400 hover:underline cursor-pointer"
                  >
                    Reset filters
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Catalog Error State */}
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
                type="button"
                onClick={() => loadCatalog(activeSearch, selectedCategory, page)}
                className="rounded-lg bg-rose-600 px-4 py-2 text-xs font-semibold text-white hover:bg-rose-500 transition cursor-pointer"
              >
                Retry
              </button>
            </div>
          )}

          {/* Catalog Loading Skeleton Grid */}
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

          {/* Catalog Empty State */}
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
                type="button"
                onClick={handleClearFilters}
                className="rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-2 text-xs font-semibold text-zinc-200 hover:bg-zinc-700 hover:text-white transition cursor-pointer"
              >
                Clear filters & view all products
              </button>
            </div>
          )}

          {/* Catalog Product Cards Grid */}
          {!loadingProducts && !productError && products.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  onAddToCart={handleAddToCart}
                  onOpenDetails={handleOpenProductDetail}
                  isAdding={addingProductId === product.id}
                />
              ))}
            </div>
          )}

          {/* Pagination Controls */}
          {!loadingProducts && !productError && totalPages > 1 && (
            <div className="flex items-center justify-center gap-4 pt-6 border-t border-zinc-800/60">
              <button
                type="button"
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
                type="button"
                onClick={handleNextPage}
                disabled={page >= totalPages}
                className="rounded-lg border border-zinc-800 bg-zinc-900 px-3.5 py-2 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
              >
                Next →
              </button>
            </div>
          )}
        </section>
      </main>

      {/* Product Detail Modal (Authoritative Backend Data) */}
      {isDetailModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto"
          onClick={(e) => {
            if (e.target === e.currentTarget) handleCloseProductDetail();
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby="product-detail-title"
        >
          <div className="relative w-full max-w-xl rounded-2xl border border-zinc-800 bg-zinc-900/95 p-6 sm:p-8 shadow-2xl shadow-purple-950/20 space-y-6 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-500/30 bg-purple-950/40 px-3 py-0.5 text-xs font-semibold text-purple-300">
                  <span>✨</span>
                  <span>Product Details</span>
                </span>
                {detailProduct && (
                  <span className="inline-flex items-center gap-1 rounded-md bg-zinc-800 px-2 py-0.5 text-[11px] font-medium text-zinc-300">
                    <span>{CATEGORY_ICONS[detailProduct.category || ""] || "🏷️"}</span>
                    <span>{detailProduct.category || "General"}</span>
                  </span>
                )}
              </div>

              <button
                type="button"
                onClick={handleCloseProductDetail}
                className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-white text-base font-bold transition cursor-pointer"
                aria-label="Close product details modal"
              >
                ✕
              </button>
            </div>

            {/* Modal Content: Loading State */}
            {detailLoading && (
              <div className="py-16 text-center space-y-3">
                <div className="text-3xl animate-spin inline-block">⏳</div>
                <h4 className="text-sm font-bold text-zinc-200">
                  Loading authoritative product details...
                </h4>
                <p className="text-xs font-mono text-zinc-500">
                  GET /api/products/{detailProductId}
                </p>
              </div>
            )}

            {/* Modal Content: Error State */}
            {detailError && !detailLoading && (
              <div className="rounded-xl border border-rose-900/50 bg-rose-950/30 p-6 text-center space-y-3">
                <div className="text-2xl">⚠️</div>
                <h4 className="text-sm font-bold text-rose-300">
                  Failed to load product details
                </h4>
                <p className="text-xs text-rose-400">{detailError}</p>
                <div className="pt-2 flex justify-center gap-3">
                  <button
                    type="button"
                    onClick={() => detailProductId && handleOpenProductDetail(detailProductId)}
                    className="rounded-lg bg-rose-600 px-3.5 py-1.5 text-xs font-semibold text-white hover:bg-rose-500 transition cursor-pointer"
                  >
                    Retry
                  </button>
                  <button
                    type="button"
                    onClick={handleCloseProductDetail}
                    className="rounded-lg border border-zinc-700 bg-zinc-800 px-3.5 py-1.5 text-xs font-semibold text-zinc-300 hover:bg-zinc-700 hover:text-white transition cursor-pointer"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}

            {/* Modal Content: Authoritative Product Details */}
            {detailProduct && !detailLoading && (
              <div className="space-y-6">
                {/* Title & SKU */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <h2
                      id="product-detail-title"
                      className="text-xl sm:text-2xl font-bold text-white tracking-tight"
                    >
                      {detailProduct.name}
                    </h2>
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold shrink-0 ${
                        detailProduct.inventory > 0
                          ? "bg-emerald-950/60 text-emerald-400 border border-emerald-900/50"
                          : "bg-rose-950/60 text-rose-400 border border-rose-900/50"
                      }`}
                    >
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          detailProduct.inventory > 0 ? "bg-emerald-400" : "bg-rose-400"
                        }`}
                      />
                      <span>
                        {detailProduct.inventory > 0
                          ? `${detailProduct.inventory} in stock`
                          : "Out of stock"}
                      </span>
                    </span>
                  </div>
                  <p className="text-xs font-mono text-zinc-400">
                    SKU: <strong className="text-zinc-200">{detailProduct.sku}</strong>
                  </p>
                </div>

                {/* Description */}
                <div className="space-y-1.5">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                    Description
                  </h4>
                  <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">
                    {detailProduct.description || "No description provided."}
                  </p>
                </div>

                {/* Attributes / Specifications */}
                {detailProduct.attributes &&
                  Object.keys(detailProduct.attributes).length > 0 && (
                    <div className="space-y-2 pt-2 border-t border-zinc-800/80">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                        Specifications & Attributes
                      </h4>
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                        {Object.entries(detailProduct.attributes).map(([key, val]) => (
                          <div
                            key={key}
                            className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-2.5 text-xs space-y-0.5"
                          >
                            <span className="text-[10px] uppercase font-semibold text-zinc-500 block truncate">
                              {key.replace(/_/g, " ")}
                            </span>
                            <span className="font-medium text-zinc-200 block truncate">
                              {String(val)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                {/* Price, Stock & Action Footer */}
                <div className="pt-4 border-t border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <span className="text-[10px] uppercase font-semibold text-zinc-500 block">
                      Authoritative Price (INR)
                    </span>
                    <span className="text-2xl font-black text-white tracking-tight">
                      {formatCurrency(detailProduct.price)}
                    </span>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => handleAddToCart(detailProduct)}
                      disabled={detailProduct.inventory <= 0 || addingProductId === detailProduct.id}
                      className={`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-xs font-semibold shadow-md transition-all cursor-pointer ${
                        detailProduct.inventory > 0
                          ? "bg-indigo-600 text-white shadow-indigo-600/30 hover:bg-indigo-500 disabled:opacity-50"
                          : "bg-zinc-800 text-zinc-500 cursor-not-allowed"
                      }`}
                    >
                      <span>{addingProductId === detailProduct.id ? "⏳" : "🛒"}</span>
                      <span>
                        {addingProductId === detailProduct.id
                          ? "Adding..."
                          : detailProduct.inventory > 0
                          ? "Add to Cart"
                          : "Sold Out"}
                      </span>
                    </button>
                    <button
                      type="button"
                      onClick={handleCloseProductDetail}
                      className="rounded-xl border border-zinc-700 bg-zinc-800 px-4 py-2.5 text-xs font-semibold text-zinc-300 hover:bg-zinc-700 hover:text-white transition cursor-pointer"
                    >
                      Close
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

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
                type="button"
                onClick={() => {
                  setShowAuthModal(false);
                  setAuthPromptReason(null);
                }}
                className="text-zinc-500 hover:text-zinc-300 text-sm font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>

            {authPromptReason && (
              <div className="rounded-xl border border-indigo-500/40 bg-indigo-950/40 p-3 text-xs font-medium text-indigo-300">
                {authPromptReason}
              </div>
            )}

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
                  onClick={fillDemoCustomer}
                  className="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-xs font-semibold text-zinc-400 hover:text-zinc-200 transition cursor-pointer"
                >
                  Demo Customer
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
