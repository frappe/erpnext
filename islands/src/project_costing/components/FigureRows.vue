<script setup>
import { List, ListCell, ListRow } from "frappe-ui/list";

// Label and figure pairs, such as "Estimated cost  ₹12 L", as a frappe-ui List.
defineProps({
	// [{ label, caption?, value, detail?, tone? }]; `tone` is an ink class for the value
	rows: { type: Array, required: true },
});
</script>

<template>
	<List :columns="['minmax(0,1fr)', 'auto']" :row-height="40">
		<ListRow v-for="row in rows" :key="row.label">
			<ListCell>
				<div class="min-w-0">
					<p class="truncate text-sm text-ink-gray-7">{{ row.label }}</p>
					<p v-if="row.caption" class="truncate text-xs text-ink-gray-5">{{ row.caption }}</p>
				</div>
			</ListCell>
			<ListCell class="justify-end">
				<div class="text-right">
					<p class="text-sm tabular-nums" :class="row.tone || 'text-ink-gray-8'">{{ row.value }}</p>
					<p v-if="row.detail" class="text-xs tabular-nums text-ink-gray-5">{{ row.detail }}</p>
				</div>
			</ListCell>
		</ListRow>
	</List>
</template>
