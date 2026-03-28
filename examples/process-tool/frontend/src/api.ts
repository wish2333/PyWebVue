import type { ApiResult } from "@/types";

/**
 * Check whether the pywebview bridge object is available.
 */
function isPywebviewReady(): boolean {
  return (
    typeof window !== "undefined" &&
    !!(window as unknown as Record<string, unknown>).pywebview
  );
}

/**
 * Wait for pywebview to be ready.
 *
 * Uses three strategies in order:
 * 1. Synchronous check for window.pywebview (already injected).
 * 2. Listen for the 'pywebviewready' DOM event.
 * 3. Polling fallback (200ms interval) in case the event fired
 *    before this function was called (race condition with Vite HMR
 *    or async module loading).
 */
export function waitForReady(): Promise<void> {
  return new Promise((resolve) => {
    if (isPywebviewReady()) {
      resolve();
      return;
    }

    let settled = false;
    const done = () => {
      if (settled) return;
      settled = true;
      clearInterval(timer);
      resolve();
    };

    // Strategy 2: event listener (pywebview dispatches on window, NOT document)
    window.addEventListener("pywebviewready", done, { once: true });

    // Strategy 3: polling fallback (race-condition guard)
    const timer = setInterval(() => {
      if (isPywebviewReady()) done();
    }, 200);

    // Safety: stop polling after 30 s to avoid leaking timers
    setTimeout(() => clearInterval(timer), 30_000);
  });
}

/**
 * Call a backend API method and return the typed result.
 */
export async function call<T = unknown>(
  method: string,
  ...args: unknown[]
): Promise<ApiResult<T>> {
  const api = (window as unknown as Record<string, unknown>).pywebview as
    | { api: Record<string, (...a: unknown[]) => Promise<unknown>> }
    | undefined;

  if (!api?.api) {
    return {
      code: 3002,
      msg: "backend is not ready",
      data: null as T,
    };
  }

  const fn = api.api[method];
  if (typeof fn !== "function") {
    return {
      code: 1,
      msg: `API method not found: ${method}`,
      data: null as T,
    };
  }

  try {
    const result = await fn(...args);
    return result as ApiResult<T>;
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e);
    return {
      code: 3001,
      msg: `backend call failed: ${message}`,
      data: null as T,
    };
  }
}
