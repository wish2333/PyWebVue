<script setup lang="ts">
import type { ColumnDef } from "@/types";

defineProps<{
  columns: ColumnDef[];
  rows: Record<string, unknown>[];
  emptyText?: string;
}>();
</script>

<template>
  <div class="overflow-x-auto">
    <table class="table table-zebra">
      <thead>
        <tr>
          <th
            v-for="col in columns"
            :key="col.key"
            :style="col.width ? { width: col.width } : undefined"
          >
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="rows.length === 0">
          <td :colspan="columns.length" class="text-center text-base-content/40">
            {{ emptyText ?? "No data" }}
          </td>
        </tr>
        <tr v-for="(row, rowIdx) in rows" :key="rowIdx">
          <td v-for="col in columns" :key="col.key">
            {{ row[col.key] ?? "" }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
