<script setup lang="ts">
import type { StatusState } from "@/types";

defineProps<{
  status: StatusState;
}>();

const STATUS_MAP: Record<StatusState, { label: string; color: string }> = {
  idle: { label: "Idle", color: "badge-ghost" },
  running: { label: "Running", color: "badge-primary" },
  paused: { label: "Paused", color: "badge-warning" },
  error: { label: "Error", color: "badge-error" },
  done: { label: "Done", color: "badge-success" },
};
</script>

<template>
  <span class="badge badge-sm" :class="STATUS_MAP[status].color">
    {{ STATUS_MAP[status].label }}
  </span>
</template>
