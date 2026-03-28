<script setup lang="ts">
import { ref, reactive, onMounted, provide } from "vue";
import { waitForReady, call } from "@/api";
import { useEvent } from "@/event-bus";
import { isOk } from "@/types";
import type { ToastOptions, ProgressPayload, FileInfo, HashResult } from "@/types";
import FileDrop from "@/components/FileDrop.vue";
import FileInfoCard from "@/components/FileInfoCard.vue";
import ProgressBar from "@/components/ProgressBar.vue";
import LogPanel from "@/components/LogPanel.vue";
import Toast from "@/components/Toast.vue";

const backendReady = ref(false);
const debugLog = ref<string[]>([]);
const progress = ref<ProgressPayload | null>(null);
const processing = ref(false);
const fileList = ref<FileInfo[]>([]);
const selectedIdx = ref(0);
const hashResult = ref<HashResult | null>(null);

const selectedFile = ref<FileInfo | null>(null);

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
useEvent("file:dropped", async (data) => {
  const { path } = data as { path: string };
  debugLog.value = [...debugLog.value, `[EVENT] file:dropped -> ${path}`];
  showToast({ type: "info", message: `File received: ${path}` });
  await addFile(path);
});

useEvent("progress:update", (data) => {
  progress.value = data as ProgressPayload;
  if ((data as ProgressPayload).current === 0) {
    processing.value = false;
  }
});

useEvent("hash:complete", (data) => {
  hashResult.value = data as HashResult;
  showToast({ type: "success", message: `Hash complete: ${(data as HashResult).name}` });
  processing.value = false;
});

useEvent("hash:error", (data) => {
  const payload = data as { message: string };
  showToast({ type: "error", message: `Hash failed: ${payload.message}` });
  processing.value = false;
});

useEvent("log:add", (data) => {
  const entry = data as { level: string; message: string };
  console.log(`[${entry.level}] ${entry.message}`);
});

// -- API calls ----------------------------------------------------------
async function addFile(path: string) {
  const result = await call<FileInfo>("get_file_info", path);
  if (isOk(result)) {
    const info = result.data;
    // Avoid duplicates
    const exists = fileList.value.some((f) => f.path === info.path);
    if (!exists) {
      fileList.value = [...fileList.value, info];
      selectFile(fileList.value.length - 1);
    } else {
      selectFile(fileList.value.findIndex((f) => f.path === info.path));
    }
  } else {
    showToast({ type: "error", message: `Failed to read file: ${result.msg}` });
  }
}

function selectFile(idx: number) {
  selectedIdx.value = idx;
  selectedFile.value = fileList.value[idx] ?? null;
  hashResult.value = null;
}

async function browseFiles() {
  if (!backendReady.value || processing.value) return;
  debugLog.value = [...debugLog.value, "[CALL] browse_files() ..."];
  try {
    const result = await call("browse_files");
    debugLog.value = [...debugLog.value, `[CALL] browse_files() -> code=${result.code} msg=${result.msg}`];
    if (!isOk(result)) {
      if (result.code !== 2) {
        showToast({ type: "error", message: result.msg });
      }
    }
  } catch (e) {
    debugLog.value = [...debugLog.value, `[CALL] browse_files() EXCEPTION: ${e}`];
    showToast({ type: "error", message: String(e) });
  }
}

async function computeHash() {
  if (!selectedFile.value || processing.value) return;
  processing.value = true;
  progress.value = null;
  hashResult.value = null;
  const result = await call("compute_hash", selectedFile.value.path);
  if (!isOk(result)) {
    showToast({ type: "error", message: result.msg });
    processing.value = false;
  }
}

function removeFile(idx: number) {
  fileList.value = fileList.value.filter((_, i) => i !== idx);
  if (fileList.value.length === 0) {
    selectedFile.value = null;
    selectedIdx.value = 0;
    hashResult.value = null;
  } else if (selectedIdx.value >= fileList.value.length) {
    selectFile(fileList.value.length - 1);
  } else {
    selectFile(selectedIdx.value);
  }
}

// -- Lifecycle -----------------------------------------------------------
onMounted(async () => {
  debugLog.value = [...debugLog.value, `pywebview=${!!window.pywebview} pywebvue=${!!window.pywebvue}`];
  try {
    await waitForReady();
    backendReady.value = true;
    // Dump what's actually on the API object
    const api = (window as unknown as Record<string, unknown>).pywebview as
      { api: Record<string, unknown> } | undefined;
    if (api?.api) {
      debugLog.value = [...debugLog.value, `api keys: ${Object.keys(api.api).join(', ')}`];
    } else {
      debugLog.value = [...debugLog.value, `api is missing or has no .api`];
    }
    debugLog.value = [...debugLog.value, `pywebvue=${!!window.pywebvue} pywebvue.event=${!!window.pywebvue?.event}`];
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
        <span v-if="fileList.length > 0" class="badge badge-outline badge-sm ml-2">
          {{ fileList.length }} file(s)
        </span>
      </div>
      <div class="flex-none gap-2">
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

        <!-- Browse button -->
        <button
          class="btn btn-outline btn-sm"
          :disabled="!backendReady || processing"
          @click="browseFiles"
        >
          Browse Files...
        </button>

        <!-- File list tabs -->
        <div v-if="fileList.length > 0" class="card bg-base-100 shadow">
          <div class="card-body p-3">
            <div class="flex gap-2 overflow-x-auto">
              <button
                v-for="(f, idx) in fileList"
                :key="f.path"
                class="btn btn-sm whitespace-nowrap"
                :class="idx === selectedIdx ? 'btn-primary' : 'btn-ghost'"
                @click="selectFile(idx)"
              >
                {{ f.name }}
                <span
                  class="btn btn-ghost btn-xs ml-1 opacity-50 hover:opacity-100"
                  @click.stop="removeFile(idx)"
                >
                  x
                </span>
              </button>
            </div>
          </div>
        </div>

        <FileInfoCard :file-info="selectedFile" />

        <!-- Hash computation -->
        <div v-if="selectedFile" class="card bg-base-100 shadow">
          <div class="card-body">
            <h2 class="card-title text-sm">Hash Computation</h2>
            <button
              class="btn btn-primary btn-sm"
              :disabled="!backendReady || processing"
              @click="computeHash"
            >
              {{ processing ? "Computing..." : "Calculate MD5 & SHA-256" }}
            </button>

            <div v-if="hashResult" class="mt-2 space-y-2">
              <div class="overflow-x-auto">
                <table class="table table-sm">
                  <tbody>
                    <tr>
                      <td class="font-medium w-24">MD5</td>
                      <td class="font-mono text-xs break-all select-all">{{ hashResult.md5 }}</td>
                    </tr>
                    <tr>
                      <td class="font-medium">SHA-256</td>
                      <td class="font-mono text-xs break-all select-all">{{ hashResult.sha256 }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <ProgressBar :progress="progress" />
        <LogPanel />

        <!-- Debug panel (temporary) -->
        <div class="card bg-base-100 shadow">
          <div class="card-body">
            <h2 class="card-title text-sm">Debug</h2>
            <pre class="text-xs bg-base-200 p-2 rounded overflow-auto max-h-40">{{ debugLog.join('\n') || '(empty)' }}</pre>
          </div>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="footer footer-center p-2 bg-base-100 text-base-content text-xs">
      <p>PyWebVue File Tool Example - Drop or browse files to inspect metadata and compute hashes</p>
    </footer>
  </div>
</template>
