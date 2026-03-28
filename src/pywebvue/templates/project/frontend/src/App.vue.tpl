<script setup lang="ts">
import { ref, onMounted, provide, reactive } from "vue";
import { waitForReady, call } from "@/api";
import { useEvent } from "@/event-bus";
import { isOk } from "@/types";
import type { ToastOptions, LogEntry, ProgressPayload } from "@/types";
import FileDrop from "@/components/FileDrop.vue";
import LogPanel from "@/components/LogPanel.vue";
import ProgressBar from "@/components/ProgressBar.vue";
import Toast from "@/components/Toast.vue";

const version = ref("0.1.0");
const backendReady = ref(false);
const lastApiResult = ref("");
const progress = ref<ProgressPayload | null>(null);

// -- Toast provide/inject -----------------------------------------------
const toastQueue = reactive<ToastOptions[]>([]);

function showToast(options: ToastOptions) {
  toastQueue.push({ ...options });
}

function removeToast(index: number) {
  toastQueue.splice(index, 1);
}

provide("toast", { showToast });
provide("version", version);

// -- Event subscriptions -------------------------------------------------
useEvent("log:add", (data) => {
  const entry = data as LogEntry;
  console.log(`[${entry.level}] ${entry.message}`);
});

useEvent("progress:update", (data) => {
  progress.value = data as ProgressPayload;
});

useEvent("file:dropped", (data) => {
  const { path } = data as { path: string };
  showToast({ type: "info", message: `File received: ${path}` });
});

// -- API calls ----------------------------------------------------------
async function checkHealth() {
  lastApiResult.value = "Calling health_check...";
  const result = await call<{ status: string }>("health_check");
  if (isOk(result)) {
    lastApiResult.value = `OK - status: ${result.data.status}`;
  } else {
    lastApiResult.value = `FAILED - ${result.msg}`;
  }
}

// -- Lifecycle -----------------------------------------------------------
onMounted(async () => {
  try {
    await waitForReady();
    backendReady.value = true;
    lastApiResult.value = "Backend connected";
  } catch {
    lastApiResult.value = "Backend not available (running outside pywebview)";
  }
});
</script>

<template>
  <Toast :items="toastQueue" @dismiss="removeToast" />

  <div class="flex flex-col h-screen bg-base-200">
    <!-- Navbar -->
    <nav class="navbar bg-base-100 shadow-md px-4">
      <div class="flex-1">
        <span class="text-lg font-bold">{{PROJECT_TITLE}}</span>
        <span class="badge badge-ghost ml-2">v{{ version }}</span>
      </div>
      <div class="flex-none">
        <span
          class="badge"
          :class="backendReady ? 'badge-success' : 'badge-warning'"
        >
          {{ backendReady ? "Connected" : "Connecting..." }}
        </span>
      </div>
    </nav>

    <!-- Main content -->
    <main class="flex-1 overflow-auto p-4">
      <div class="max-w-4xl mx-auto space-y-4">
        <!-- Health check -->
        <div class="card bg-base-100 shadow">
          <div class="card-body">
            <h2 class="card-title">Actions</h2>
            <div class="card-actions">
              <button
                class="btn btn-primary btn-sm"
                :disabled="!backendReady"
                @click="checkHealth"
              >
                Health Check
              </button>
            </div>
          </div>
        </div>

        <!-- File drop -->
        <FileDrop />

        <!-- Progress -->
        <ProgressBar :progress="progress" />

        <!-- Log panel -->
        <LogPanel />
      </div>
    </main>

    <!-- Footer -->
    <footer class="footer footer-center p-2 bg-base-100 text-base-content text-xs">
      <p>
        Backend:
        <span :class="backendReady ? 'text-success' : 'text-warning'">
          {{ backendReady ? "Online" : "Offline" }}
        </span>
        <span class="mx-2">|</span>
        Last API: {{ lastApiResult }}
      </p>
    </footer>
  </div>
</template>
