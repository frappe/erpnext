<script setup>
import { List, ListCell, ListRow } from "frappe-ui/list";

// Label and figure pairs, such as "Estimated cost  ₹12 L", as a frappe-ui List.
defineProps({
	// [{ label, value, tone? }]; `tone` is an ink class for the value
	rows: { type: Array, required: true },
});
</script>

<template>
	<List :columns="['minmax(0,1fr)', 'auto']" :row-height="40">
		<ListRow v-for="row in rows" :key="row.label">
			<ListCell>
				<p class="truncate text-sm text-ink-gray-7">{{ row.label }}</p>
			</ListCell>
			<ListCell class="justify-end">
				<p class="text-sm tabular-nums" :class="row.tone || 'text-ink-gray-8'">{{ row.value }}</p>
			</ListCell>
		</ListRow>
	</List>
</template>
