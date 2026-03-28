<script setup lang="ts">
import { computed } from "vue";
import type { ProgressPayload } from "@/types";

const props = defineProps<{
  progress: ProgressPayload | null;
}>();

const percentage = computed(() => {
  if (!props.progress) return 0;
  const { current, total } = props.progress;
  if (total <= 0) return 0;
  return Math.min(100, Math.round((current / total) * 100));
});

const label = computed(() => {
  if (!props.progress) return "";
  return props.progress.label ?? `${props.progress.current}/${props.progress.total}`;
});

const barClass = computed(() => {
  const pct = percentage.value;
  if (pct >= 100) return "progress-success";
  if (pct >= 50) return "progress-primary";
  return "progress-warning";
});

const isComplete = computed(() => percentage.value >= 100);
</script>

<template>
  <div class="card bg-base-100 shadow">
    <div class="card-body">
      <div class="flex items-center justify-between">
        <h2 class="card-title text-sm">Progress</h2>
        <span
          v-if="progress"
          class="badge badge-sm"
          :class="isComplete ? 'badge-success' : 'badge-primary'"
        >
          {{ percentage }}%
        </span>
        <span v-else class="badge badge-sm badge-ghost">Idle</span>
      </div>

      <progress
        class="progress w-full"
        :class="progress ? barClass : 'progress-info'"
        :value="progress ? percentage : undefined"
        max="100"
      />

      <p v-if="progress && label" class="text-xs text-base-content/60">{{ label }}</p>
      <p v-else-if="!progress" class="text-xs text-base-content/40">No active progress</p>
    </div>
  </div>
</template>
