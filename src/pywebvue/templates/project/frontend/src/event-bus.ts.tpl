import { onMounted, onUnmounted } from "vue";

type EventCallback = (data: unknown) => void;

/**
 * Wait for the pywebvue bridge to be injected by the Python backend.
 *
 * The bridge JS is injected via evaluate_js in ApiBase.bind_window(), which
 * fires after pywebview's 'loaded' event -- later than Vue's onMounted.
 *
 * Uses three strategies:
 * 1. Synchronous check for window.pywebvue.event (already injected).
 * 2. Listen for the 'pywebvueready' DOM event (dispatched by BRIDGE_JS).
 * 3. Polling fallback (200ms) for cases where the event is missed.
 */
function waitForBridge(): Promise<void> {
  return new Promise((resolve) => {
    if (window.pywebvue?.event) {
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

    // Strategy 2: event listener
    document.addEventListener("pywebvueready", done, { once: true });

    // Strategy 3: polling fallback
    const timer = setInterval(() => {
      if (window.pywebvue?.event) done();
    }, 200);

    // Safety: stop polling after 30 s
    setTimeout(() => clearInterval(timer), 30_000);
  });
}

/**
 * Composable that subscribes to a pywebvue event for the component lifetime.
 *
 * @param name     - Event name in 'module:action' format.
 * @param callback - Handler called with the event payload.
 */
export function useEvent(name: string, callback: EventCallback): void {
  onMounted(async () => {
    await waitForBridge();
    window.pywebvue.event.on(name, callback);
  });
  onUnmounted(() => {
    if (window.pywebvue?.event) {
      window.pywebvue.event.off(name, callback);
    }
  });
}

/**
 * Wait for a one-time pywebvue event, with optional timeout.
 *
 * @param name    - Event name to listen for.
 * @param timeout - Maximum wait time in milliseconds (default: 30000).
 */
export async function waitForEvent<T = unknown>(
  name: string,
  timeout = 30000
): Promise<T> {
  await waitForBridge();
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => {
      window.pywebvue.event.off(name, handler);
      reject(new Error(`Timeout waiting for event: ${name}`));
    }, timeout);

    const handler = (data: unknown) => {
      clearTimeout(timer);
      resolve(data as T);
    };

    window.pywebvue.event.on(name, handler);
  });
}
