<script setup lang="ts">
import { ref, watch, nextTick } from "vue";
import type { ToastOptions } from "@/types";

const props = defineProps<{
  items: ToastOptions[];
}>();

const emit = defineEmits<{
  dismiss: [index: number];
}>();

const AUTO_DISMISS_MS = 4000;

const localItems = ref<ToastOptions[]>([]);

watch(
  () => props.items,
  async (newItems) => {
    if (newItems.length > localItems.value.length) {
      const added = newItems.slice(localItems.value.length);
      localItems.value = [...newItems];
      for (const _item of added) {
        await nextTick();
        setTimeout(() => {
          const index = localItems.value.indexOf(_item);
          if (index >= 0) {
            localItems.value = localItems.value.filter((i) => i !== _item);
            const originalIndex = props.items.indexOf(_item);
            if (originalIndex >= 0) {
              emit("dismiss", originalIndex);
            }
          }
        }, AUTO_DISMISS_MS);
      }
    } else {
      localItems.value = [...newItems];
    }
  }
);

const toastTypeClass: Record<string, string> = {
  success: "alert-success",
  error: "alert-error",
  warning: "alert-warning",
  info: "alert-info",
};
</script>

<template>
  <Teleport to="body">
    <div class="toast toast-top toast-end z-50">
      <div
        v-for="item in localItems"
        :key="item.id"
        class="alert shadow-lg"
        :class="toastTypeClass[item.type] ?? 'alert-info'"
      >
        <span>{{ item.message }}</span>
        <button
          class="btn btn-sm btn-ghost"
          @click="
            () => {
              const idx = localItems.indexOf(item);
              if (idx >= 0) {
                localItems.value = localItems.value.filter((i) => i !== item);
                emit('dismiss', props.items.indexOf(item));
              }
            }
          "
        >
          X
        </button>
      </div>
    </div>
  </Teleport>
</template>
