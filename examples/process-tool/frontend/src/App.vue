<script setup lang="ts">
import { ref, reactive, computed, onMounted, provide } from "vue";
import { waitForReady, call } from "@/api";
import { useEvent } from "@/event-bus";
import { isOk } from "@/types";
import type { ToastOptions, StatusState, ProcessStatus, PresetCommand, SystemInfo } from "@/types";
import StatusBadge from "@/components/StatusBadge.vue";
import LogPanel from "@/components/LogPanel.vue";
import Toast from "@/components/Toast.vue";

const backendReady = ref(false);
const processState = ref<StatusState>("idle");
const pid = ref<number | null>(null);
const timeoutRemaining = ref<number | null>(null);
const outputCount = ref<number>(0);
const elapsed = ref<number | null>(null);
const cmdInput = ref("");
const cmdTimeout = ref("");
const presets = ref<PresetCommand[]>([]);
const sysInfo = ref<SystemInfo | null>(null);
const showSysInfo = ref(false);

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
    outputCount.value = result.data.output_count;
    elapsed.value = result.data.elapsed;
  }
}

async function loadPresets() {
  const result = await call<{ presets: PresetCommand[] }>("get_presets");
  if (isOk(result)) {
    presets.value = result.data.presets;
  }
}

async function loadSystemInfo() {
  const result = await call<SystemInfo>("get_system_info");
  if (isOk(result)) {
    sysInfo.value = result.data;
  }
}

function selectPreset(preset: PresetCommand) {
  cmdInput.value = preset.command;
  cmdTimeout.value = preset.timeout;
}

async function startProcess() {
  if (!cmdInput.value.trim()) return;
  const timeout = cmdTimeout.value ? parseInt(cmdTimeout.value, 10) : null;
  const result = await call("start_task", cmdInput.value.trim(), timeout);
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
    outputCount.value = 0;
    elapsed.value = null;
  }
}

async function toggleSysInfo() {
  showSysInfo.value = !showSysInfo.value;
  if (showSysInfo.value && !sysInfo.value) {
    await loadSystemInfo();
  }
}

// -- Lifecycle -----------------------------------------------------------
onMounted(async () => {
  try {
    await waitForReady();
    backendReady.value = true;
    refreshStatus();
    loadPresets();
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
        <StatusBadge :status="processState" :elapsed="elapsed" />
        <span v-if="pid" class="badge badge-outline badge-sm">PID: {{ pid }}</span>
        <span v-if="outputCount > 0" class="badge badge-outline badge-sm">{{ outputCount }} lines</span>
        <span v-if="elapsed !== null && (processState === 'running' || processState === 'paused')" class="badge badge-outline badge-sm">
          {{ elapsed }}s
        </span>
        <span v-if="timeoutRemaining !== null" class="badge badge-outline badge-sm">Timeout: {{ timeoutRemaining }}s</span>
        <button
          class="btn btn-ghost btn-xs"
          :disabled="!backendReady"
          @click="toggleSysInfo"
        >
          {{ showSysInfo ? 'Hide' : 'System Info' }}
        </button>
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

        <!-- System Info panel (collapsible) -->
        <div v-if="showSysInfo" class="card bg-base-100 shadow">
          <div class="card-body">
            <h2 class="card-title">System Information</h2>
            <div v-if="!sysInfo" class="text-base-content/40 text-sm">Loading...</div>
            <div v-else class="overflow-x-auto">
              <table class="table table-sm">
                <tbody>
                  <tr>
                    <td class="font-medium w-40">Hostname</td>
                    <td class="font-mono text-sm">{{ sysInfo.hostname }}</td>
                  </tr>
                  <tr>
                    <td class="font-medium">OS</td>
                    <td class="text-sm">{{ sysInfo.system }} {{ sysInfo.release }}</td>
                  </tr>
                  <tr>
                    <td class="font-medium">Architecture</td>
                    <td class="text-sm">{{ sysInfo.machine }}</td>
                  </tr>
                  <tr>
                    <td class="font-medium">Python</td>
                    <td class="text-sm">{{ sysInfo.python_version }}</td>
                  </tr>
                  <tr>
                    <td class="font-medium">CPU Cores</td>
                    <td class="text-sm">{{ sysInfo.cpu_count ?? 'N/A' }}</td>
                  </tr>
                  <tr>
                    <td class="font-medium">CPU Usage</td>
                    <td class="text-sm">{{ sysInfo.cpu_percent !== null ? `${sysInfo.cpu_percent}%` : 'N/A (install psutil)' }}</td>
                  </tr>
                  <tr v-if="sysInfo.memory_total">
                    <td class="font-medium">Memory</td>
                    <td class="text-sm">
                      {{ sysInfo.memory_used_display }} / {{ sysInfo.memory_total_display }}
                      ({{ sysInfo.memory_percent?.toFixed(1) }}%)
                    </td>
                  </tr>
                  <tr v-else>
                    <td class="font-medium">Memory</td>
                    <td class="text-sm text-base-content/40">N/A (install psutil for memory info)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Preset commands -->
        <div v-if="presets.length > 0" class="card bg-base-100 shadow">
          <div class="card-body p-3">
            <h2 class="card-title text-sm mb-2">Quick Presets</h2>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="preset in presets"
                :key="preset.name"
                class="btn btn-sm btn-outline"
                :disabled="!canStart"
                :title="preset.description"
                @click="selectPreset(preset)"
              >
                {{ preset.name }}
              </button>
            </div>
          </div>
        </div>

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

            <!-- Timeout input -->
            <div class="flex items-center gap-2 mt-2">
              <label class="text-sm text-base-content/60">Timeout (s):</label>
              <input
                v-model="cmdTimeout"
                type="number"
                class="input input-bordered input-sm input-number w-24"
                min="0"
                placeholder="No limit"
              />
            </div>

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
