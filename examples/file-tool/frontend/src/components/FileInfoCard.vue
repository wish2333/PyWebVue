<script setup lang="ts">
import type { FileInfo } from "@/types";
import { CATEGORY_STYLE } from "@/types";

defineProps<{
  fileInfo: FileInfo | null;
}>();
</script>

<template>
  <div class="card bg-base-100 shadow">
    <div class="card-body">
      <h2 class="card-title">File Information</h2>

      <div v-if="!fileInfo" class="text-base-content/40 text-sm">
        Drop or select a file to view its metadata.
      </div>

      <div v-else class="overflow-x-auto">
        <table class="table table-sm">
          <tbody>
            <tr>
              <td class="font-medium w-36">Name</td>
              <td class="font-mono text-sm">{{ fileInfo.name }}</td>
            </tr>
            <tr>
              <td class="font-medium">Extension</td>
              <td>
                <span class="badge badge-outline badge-sm">{{ fileInfo.extension }}</span>
              </td>
            </tr>
            <tr>
              <td class="font-medium">Category</td>
              <td>
                <span
                  class="badge badge-sm"
                  :class="CATEGORY_STYLE[fileInfo.category]?.color ?? 'badge-ghost'"
                >
                  {{ CATEGORY_STYLE[fileInfo.category]?.label ?? fileInfo.category }}
                </span>
              </td>
            </tr>
            <tr>
              <td class="font-medium">Size</td>
              <td>{{ fileInfo.size_display }} ({{ fileInfo.size_bytes.toLocaleString() }} bytes)</td>
            </tr>
            <tr>
              <td class="font-medium">Modified</td>
              <td class="text-sm">{{ fileInfo.modified }}</td>
            </tr>
            <tr>
              <td class="font-medium">Type</td>
              <td>
                <span class="badge badge-sm" :class="fileInfo.is_binary ? 'badge-warning' : 'badge-info'">
                  {{ fileInfo.is_binary ? 'Binary' : 'Text' }}
                </span>
              </td>
            </tr>
            <tr>
              <td class="font-medium">Path</td>
              <td class="font-mono text-xs break-all">{{ fileInfo.path }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
