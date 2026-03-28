<script setup lang="ts">
import { ref, provide, watch, nextTick } from "vue";
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
  () => props.items.length,
  async () => {
    if (props.items.length > localItems.value.length) {
      const newItems = props.items.slice(localItems.value.length);
      localItems.value = [...props.items];
      for (const _item of newItems) {
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
      localItems.value = [...props.items];
    }
  }
);

const toastTypeClass: Record<string, string> = {
  success: "alert-success",
  error: "alert-error",
  warning: "alert-warning",
  info: "alert-info",
};

interface ToastApi {
  showToast: (options: ToastOptions) => void;
}

provide<ToastApi>("toast", {
  showToast: () => {
    /* noop - parent App.vue handles the actual queue */
  },
});
</script>

<template>
  <Teleport to="body">
    <div class="toast toast-top toast-end z-50">
      <div
        v-for="(item, index) in localItems"
        :key="index"
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
                localItems = localItems.filter((i) => i !== item);
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
