<script setup lang="ts">
import { ref } from "vue";

/**
 * FileDrop component - visual drop zone indicator.
 *
 * Note: Actual file path extraction is handled by pywebview's native
 * file drop mechanism at the window level. When files are dropped onto
 * the pywebview window, the framework calls ApiBase.on_file_drop(file_paths).
 * This component only provides visual drag-over feedback.
 */
const isDragging = ref(false);

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
          Drag and drop files onto the window, or use the Browse button below
        </p>
      </div>
    </div>
  </div>
</template>
