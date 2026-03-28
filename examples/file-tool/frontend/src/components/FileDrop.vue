<script setup lang="ts">
import { ref } from "vue";
import { useEvent } from "@/event-bus";
import { inject } from "vue";
import type { ToastOptions } from "@/types";

const isDragging = ref(false);
const droppedFiles = ref<string[]>([]);

const toast = inject<{ showToast: (options: ToastOptions) => void }>("toast");

useEvent("file:dropped", (data) => {
  const entry = data as { path: string };
  if (!droppedFiles.value.includes(entry.path)) {
    droppedFiles.value = [...droppedFiles.value, entry.path];
  }
});

function onDragOver(event: DragEvent) {
  event.preventDefault();
  isDragging.value = true;
}

function onDragLeave() {
  isDragging.value = false;
}

function onDrop(event: DragEvent) {
  event.preventDefault();
  isDragging.value = false;
}
</script>

<template>
  <div class="card bg-base-100 shadow">
    <div class="card-body">
      <h2 class="card-title">File Drop</h2>

      <div
        class="border-2 border-dashed rounded-lg p-8 text-center transition-colors"
        :class="isDragging ? 'border-primary bg-primary/10' : 'border-base-300'"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
      >
        <p v-if="isDragging" class="text-primary font-semibold">
          Drop files here
        </p>
        <p v-else class="text-base-content/60">
          Drag and drop files onto the window
        </p>
      </div>

      <ul v-if="droppedFiles.length > 0" class="list-disc list-inside text-sm mt-2 space-y-1">
        <li v-for="(path, idx) in droppedFiles" :key="idx">
          {{ path }}
        </li>
      </ul>
    </div>
  </div>
</template>
