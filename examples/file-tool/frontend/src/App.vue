<script setup lang="ts">
import { ref, reactive, onMounted, provide } from "vue";
import { waitForReady, call } from "@/api";
import { useEvent } from "@/event-bus";
import { isOk } from "@/types";
import type { ToastOptions, ProgressPayload, FileInfo } from "@/types";
import FileDrop from "@/components/FileDrop.vue";
import FileInfoCard from "@/components/FileInfoCard.vue";
import ProgressBar from "@/components/ProgressBar.vue";
import LogPanel from "@/components/LogPanel.vue";
import Toast from "@/components/Toast.vue";

const backendReady = ref(false);
const progress = ref<ProgressPayload | null>(null);
const fileInfo = ref<FileInfo | null>(null);
const processing = ref(false);

// -- Toast provide/inject -----------------------------------------------
let _toastId = 0;
const toastQueue = reactive<ToastOptions[]>([]);

function showToast(options: ToastOptions) {
  toastQueue.push({ ...options, id: ++_toastId });
}

function removeToast(index: number) {
  toastQueue.splice(index, 1);
}

provide("toast", { showToast });
provide("removeToast", removeToast);

// -- Event subscriptions -------------------------------------------------
useEvent("file:dropped", (data) => {
  const { path } = data as { path: string };
  showToast({ type: "info", message: `File received: ${path}` });
  loadFileInfo(path);
});

useEvent("progress:update", (data) => {
  progress.value = data as ProgressPayload;
  if ((data as ProgressPayload).current === 0) {
    processing.value = false;
  }
});

useEvent("file:process_complete", (data) => {
  const { name } = data as { name: string };
  showToast({ type: "success", message: `Processing complete: ${name}` });
  processing.value = false;
});

useEvent("log:add", (data) => {
  const entry = data as { level: string; message: string };
  console.log(`[${entry.level}] ${entry.message}`);
});

// -- API calls ----------------------------------------------------------
async function loadFileInfo(path: string) {
  const result = await call<FileInfo>("get_file_info", path);
  if (isOk(result)) {
    fileInfo.value = result.data;
  } else {
    showToast({ type: "error", message: `Failed to read file: ${result.msg}` });
  }
}

async function processSelectedFile() {
  if (!fileInfo.value || processing.value) return;
  processing.value = true;
  progress.value = null;
  const result = await call("process_file", fileInfo.value.path);
  if (!isOk(result)) {
    showToast({ type: "error", message: result.msg });
    processing.value = false;
  }
}

// -- Lifecycle -----------------------------------------------------------
onMounted(async () => {
  try {
    await waitForReady();
    backendReady.value = true;
  } catch {
    backendReady.value = false;
  }
});
</script>

<template>
  <Toast :items="toastQueue" @dismiss="removeToast" />

  <div class="flex flex-col h-screen bg-base-200">
    <!-- Navbar -->
    <nav class="navbar bg-base-100 shadow-md px-4">
      <div class="flex-1">
        <span class="text-lg font-bold">File Tool</span>
        <span class="badge badge-ghost ml-2">Example</span>
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
        <FileDrop />
        <FileInfoCard :file-info="fileInfo" />

        <div v-if="fileInfo" class="card bg-base-100 shadow">
          <div class="card-body">
            <div class="card-actions">
              <button
                class="btn btn-primary btn-sm"
                :disabled="!backendReady || processing"
                @click="processSelectedFile"
              >
                {{ processing ? "Processing..." : "Process File" }}
              </button>
            </div>
          </div>
        </div>

        <ProgressBar :progress="progress" />
        <LogPanel />
      </div>
    </main>

    <!-- Footer -->
    <footer class="footer footer-center p-2 bg-base-100 text-base-content text-xs">
      <p>PyWebVue File Tool Example - Drop files to inspect metadata and simulate processing</p>
    </footer>
  </div>
</template>
