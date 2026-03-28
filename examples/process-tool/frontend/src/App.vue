<script setup lang="ts">
import { ref, reactive, computed, onMounted, provide } from "vue";
import { waitForReady, call } from "@/api";
import { useEvent } from "@/event-bus";
import { isOk } from "@/types";
import type { ToastOptions, StatusState, ProcessStatus } from "@/types";
import StatusBadge from "@/components/StatusBadge.vue";
import LogPanel from "@/components/LogPanel.vue";
import Toast from "@/components/Toast.vue";

const backendReady = ref(false);
const processState = ref<StatusState>("idle");
const pid = ref<number | null>(null);
const timeoutRemaining = ref<number | null>(null);
const cmdInput = ref('python -c "for i in range(10): print(f\'line {i}\'); import time; time.sleep(0.5)"');

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
useEvent("process:state_changed", (data) => {
  const payload = data as { state: string };
  const mapped: Record<string, StatusState> = {
    idle: "idle",
    running: "running",
    paused: "paused",
    stopped: "done",
  };
  processState.value = mapped[payload.state] ?? "error";
  refreshStatus();
});

useEvent("log:add", (data) => {
  const entry = data as { level: string; message: string };
  console.log(`[${entry.level}] ${entry.message}`);
});

useEvent("process:worker:timeout", (data) => {
  const payload = data as { timeout: number };
  showToast({ type: "warning", message: `Process timed out after ${payload.timeout}s` });
});

useEvent("process:worker:complete", (data) => {
  const payload = data as { returncode: number };
  if (payload.returncode === 0) {
    showToast({ type: "success", message: "Process completed successfully" });
  } else {
    showToast({ type: "error", message: `Process exited with code ${payload.returncode}` });
  }
});

// -- Computed button states -----------------------------------------------
const canStart = computed(() => processState.value === "idle" || processState.value === "done");
const canPause = computed(() => processState.value === "running");
const canResume = computed(() => processState.value === "paused");
const canStop = computed(() => processState.value === "running" || processState.value === "paused");
const canReset = computed(() => processState.value === "done");

// -- API calls ----------------------------------------------------------
async function refreshStatus() {
  const result = await call<ProcessStatus>("get_status");
  if (isOk(result)) {
    pid.value = result.data.pid;
    timeoutRemaining.value = result.data.timeout_remaining;
  }
}

async function startProcess() {
  if (!cmdInput.value.trim()) return;
  const result = await call("start_task", cmdInput.value.trim());
  if (isOk(result)) {
    showToast({ type: "info", message: "Process started" });
  } else {
    showToast({ type: "error", message: result.msg });
  }
}

async function pauseProcess() {
  const result = await call("pause_task");
  if (!isOk(result)) {
    showToast({ type: "error", message: result.msg });
  }
}

async function resumeProcess() {
  const result = await call("resume_task");
  if (!isOk(result)) {
    showToast({ type: "error", message: result.msg });
  }
}

async function stopProcess() {
  const result = await call("stop_task");
  if (!isOk(result)) {
    showToast({ type: "error", message: result.msg });
  }
}

async function resetProcess() {
  const result = await call("reset_task");
  if (isOk(result)) {
    pid.value = null;
    timeoutRemaining.value = null;
  }
}

// -- Lifecycle -----------------------------------------------------------
onMounted(async () => {
  try {
    await waitForReady();
    backendReady.value = true;
    refreshStatus();
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
        <span class="text-lg font-bold">Process Tool</span>
        <span class="badge badge-ghost ml-2">Example</span>
      </div>
      <div class="flex items-center gap-2">
        <StatusBadge :status="processState" />
        <span
          v-if="pid"
          class="badge badge-outline badge-sm"
        >
          PID: {{ pid }}
        </span>
        <span
          v-if="timeoutRemaining !== null"
          class="badge badge-outline badge-sm"
        >
          Timeout: {{ timeoutRemaining }}s
        </span>
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
        <!-- Command input -->
        <div class="card bg-base-100 shadow">
          <div class="card-body">
            <h2 class="card-title">Command</h2>
            <textarea
              v-model="cmdInput"
              class="textarea textarea-bordered w-full font-mono text-sm"
              rows="2"
              placeholder="Enter a command to run..."
              :disabled="!canStart"
            ></textarea>

            <!-- Control buttons -->
            <div class="flex flex-wrap gap-2 mt-2">
              <button
                class="btn btn-primary btn-sm"
                :disabled="!backendReady || !canStart"
                @click="startProcess"
              >
                Start
              </button>
              <button
                class="btn btn-warning btn-sm"
                :disabled="!backendReady || !canPause"
                @click="pauseProcess"
              >
                Pause
              </button>
              <button
                class="btn btn-info btn-sm"
                :disabled="!backendReady || !canResume"
                @click="resumeProcess"
              >
                Resume
              </button>
              <button
                class="btn btn-error btn-sm"
                :disabled="!backendReady || !canStop"
                @click="stopProcess"
              >
                Stop
              </button>
              <button
                class="btn btn-ghost btn-sm"
                :disabled="!backendReady || !canReset"
                @click="resetProcess"
              >
                Reset
              </button>
            </div>
          </div>
        </div>

        <!-- Log panel -->
        <LogPanel />
      </div>
    </main>

    <!-- Footer -->
    <footer class="footer footer-center p-2 bg-base-100 text-base-content text-xs">
      <p>PyWebVue Process Tool Example - Manage subprocesses with start/pause/resume/stop</p>
    </footer>
  </div>
</template>
