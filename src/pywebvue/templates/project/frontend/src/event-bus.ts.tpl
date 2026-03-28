import { onMounted, onUnmounted } from "vue";

type EventCallback = (data: unknown) => void;

/**
 * Composable that subscribes to a pywebvue event for the component lifetime.
 *
 * @param name     - Event name in 'module:action' format.
 * @param callback - Handler called with the event payload.
 */
export function useEvent(name: string, callback: EventCallback): void {
  onMounted(() => {
    window.pywebvue.event.on(name, callback);
  });
  onUnmounted(() => {
    window.pywebvue.event.off(name, callback);
  });
}

/**
 * Wait for a one-time pywebvue event, with optional timeout.
 *
 * @param name    - Event name to listen for.
 * @param timeout - Maximum wait time in milliseconds (default: 30000).
 */
export function waitForEvent<T = unknown>(
  name: string,
  timeout = 30000
): Promise<T> {
  return new Promise((resolve, reject) => {
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
