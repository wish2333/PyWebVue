import { onMounted, onUnmounted } from "vue";

type EventCallback = (data: unknown) => void;

/**
 * Set up the pywebvue event bridge on the JavaScript side.
 *
 * Normally the Python backend injects this via evaluate_js() in
 * ApiBase.bind_window().  However on pywebview 6.x (EdgeChromium),
 * evaluate_js() can silently fail to execute, leaving window.pywebvue
 * undefined.  This function acts as a fallback: it creates the bridge
 * directly on the JS side so that event listeners work regardless.
 *
 * The Python backend still dispatches events by calling
 *   evaluate_js('__pywebvue_dispatch("event", {...})')
 * which is forwarded to the same listener registry.
 */
function ensureBridge(): void {
  if (window.__pywebvue_dispatch) return;

  (window as unknown as Record<string, unknown>).__pywebvue_event_listeners = {};

  (window as unknown as Record<string, unknown>).__pywebvue_dispatch = function (
    eventName: string,
    payload: unknown,
  ) {
    const listeners = (
      window as unknown as Record<string, Record<string, EventCallback[]>>
    ).__pywebvue_event_listeners[eventName];
    if (listeners) {
      for (let i = 0; i < listeners.length; i++) {
        try {
          listeners[i](payload);
        } catch (e) {
          console.error(e);
        }
      }
    }
  };

  if (!window.pywebvue) {
    (window as unknown as Record<string, unknown>).pywebvue = {};
  }

  (window.pywebvue as unknown as Record<string, unknown>).event = {
    on(name: string, callback: EventCallback) {
      const store = (
        window as unknown as Record<string, Record<string, EventCallback[]>>
      ).__pywebvue_event_listeners;
      if (!store[name]) {
        store[name] = [];
      }
      store[name].push(callback);
    },
    off(name: string, callback: EventCallback) {
      const store = (
        window as unknown as Record<string, Record<string, EventCallback[]>>
      ).__pywebvue_event_listeners;
      const list = store[name];
      if (!list) return;
      store[name] = list.filter((cb) => cb !== callback);
    },
  };
}

/**
 * Wait for the pywebvue bridge to be available.
 *
 * Uses three strategies:
 * 1. Synchronous check for window.pywebvue.event.
 * 2. Listen for 'pywebvueready' (dispatched by BRIDGE_JS if evaluate_js works).
 * 3. Polling fallback (200ms) for cases where evaluate_js failed.
 */
function waitForBridge(): Promise<void> {
  return new Promise((resolve) => {
    // Ensure the bridge exists on the JS side even if Python's
    // evaluate_js() never ran.
    ensureBridge();

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
      ensureBridge();
      if (window.pywebvue?.event) done();
    }, 200);

    // Safety: stop polling after 30 s
    setTimeout(() => clearInterval(timer), 30_000);
  });
}

/**
 * Composable that subscribes to a pywebvue event for the component lifetime.
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
