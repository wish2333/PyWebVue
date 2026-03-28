import type { ApiResult } from "@/types";

/**
 * Wait for pywebview to be ready (the 'pywebviewready' DOM event).
 */
export function waitForReady(): Promise<void> {
  return new Promise((resolve) => {
    if (
      typeof window !== "undefined" &&
      (window as unknown as Record<string, unknown>).pywebview
    ) {
      resolve();
      return;
    }
    document.addEventListener("pywebviewready", () => resolve(), {
      once: true,
    });
  });
}

/**
 * Call a backend API method and return the typed result.
 */
export async function call<T = unknown>(
  method: string,
  ...args: unknown[]
): Promise<ApiResult<T>> {
  const api = window.pywebview?.api;
  if (!api) {
    return {
      code: 3002,
      msg: "backend is not ready",
      data: null as T,
    };
  }

  const fn = api[method];
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
