export default function Home() {
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
          An AI-powered agentic commerce platform for product discovery, recommendations, revenue growth and secure checkout.
        </p>
        <div className="mt-8 flex items-center gap-3 text-xs text-zinc-500 dark:text-zinc-500">
          <span className="rounded bg-zinc-200/70 px-2 py-1 font-mono dark:bg-zinc-800">Next.js 16</span>
          <span className="rounded bg-zinc-200/70 px-2 py-1 font-mono dark:bg-zinc-800">TypeScript</span>
          <span className="rounded bg-zinc-200/70 px-2 py-1 font-mono dark:bg-zinc-800">Tailwind CSS</span>
        </div>
      </main>
    </div>
  );
}

