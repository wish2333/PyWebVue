/// <reference types="vite/client" />

declare module "*.vue" {
  import type { DefineComponent } from "vue";
  const component: DefineComponent<object, object, unknown>;
  export default component;
}

interface PyWebVueEventBus {
  on(name: string, callback: (data: unknown) => void): void;
  off(name: string, callback: (data: unknown) => void): void;
}

interface PyWebVue {
  event: PyWebVueEventBus;
}

interface PyWebView {
  api: Record<string, (...args: unknown[]) => Promise<unknown>>;
}

interface Window {
  pywebvue: PyWebVue;
  pywebview: PyWebView;
  __pywebvue_dispatch: (eventName: string, payload: unknown) => void;
}
