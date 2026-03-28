<script setup lang="ts">
import { ref, nextTick, watch } from "vue";
import { useEvent } from "@/event-bus";
import type { LogEntry } from "@/types";

const MAX_LINES = 500;

let _logId = 0;
const logs = ref<LogEntry[]>([]);
const filterLevel = ref("ALL");
const autoScroll = ref(true);
const logContainer = ref<HTMLDivElement | null>(null);

const levelOptions = ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

useEvent("log:add", (data) => {
  const entry = { ...(data as LogEntry), id: ++_logId };
  logs.value = [...logs.value, entry];
  if (logs.value.length > MAX_LINES) {
    logs.value = logs.value.slice(-MAX_LINES);
  }
  if (autoScroll.value) {
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight;
      }
    });
  }
});

const filteredLogs = ref(logs);

watch([filterLevel, logs], ([level, allLogs]) => {
  if (level === "ALL") {
    filteredLogs.value = allLogs;
  } else {
    filteredLogs.value = allLogs.filter((e) => e.level === level);
  }
});

function clearLogs() {
  logs.value = [];
  filteredLogs.value = [];
}

function levelClass(level: string): string {
  const map: Record<string, string> = {
    DEBUG: "text-base-content/50",
    INFO: "text-info",
    WARNING: "text-warning",
    ERROR: "text-error",
    CRITICAL: "text-error font-bold",
  };
  return map[level] ?? "";
}
</script>

<template>
  <div class="card bg-base-100 shadow">
    <div class="card-body">
      <div class="flex items-center justify-between">
        <h2 class="card-title">Logs <span class="badge badge-sm badge-ghost font-normal">{{ logs.length }}</span></h2>
        <div class="flex items-center gap-2">
          <select
            v-model="filterLevel"
            class="select select-bordered select-xs"
          >
            <option v-for="level in levelOptions" :key="level" :value="level">
              {{ level }}
            </option>
          </select>
          <label class="label cursor-pointer gap-1">
            <input
              v-model="autoScroll"
              type="checkbox"
              class="checkbox checkbox-xs checkbox-primary"
            />
            <span class="label-text text-xs">Auto-scroll</span>
          </label>
          <button class="btn btn-xs btn-ghost" @click="clearLogs">Clear</button>
        </div>
      </div>

      <div
        ref="logContainer"
        class="mockup-code bg-base-200 text-xs max-h-64 overflow-y-auto"
      >
        <div v-if="filteredLogs.length === 0" class="text-base-content/40 p-2">
          No logs yet.
        </div>
        <div
          v-for="entry in filteredLogs"
          :key="entry.id"
          class="px-2 py-0.5"
          :class="levelClass(entry.level)"
        >
          <span class="text-base-content/40">[{{ entry.level }}]</span>
          {{ entry.message }}
        </div>
      </div>
    </div>
  </div>
</template>
