import { onMounted, onUnmounted } from "vue";

type EventCallback = (data: unknown) => void;

/**
 * Composable that subscribes to a pywebvue event for the component lifetime.
 */
export function useEvent(name: string, callback: EventCallback): void {
  onMounted(() => {
    window.pywebview.event.on(name, callback);
  });
  onUnmounted(() => {
    window.pywebview.event.off(name, callback);
  });
}

/**
 * Wait for a one-time pywebvue event, with optional timeout.
 */
export function waitForEvent<T = unknown>(
  name: string,
  timeout = 30000
): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      window.pywebview.event.off(name, handler);
      reject(new Error(`Timeout waiting for event: ${name}`));
    }, timeout);

    const handler = (data: unknown) => {
      clearTimeout(timer);
      resolve(data as T);
    };

    window.pywebview.event.on(name, handler);
  });
}
