<script setup>
import { ListHeader, ListHeaderCell, ListHeaderCellSort } from "frappe-ui/list";

defineProps({
	columns: { type: Array, required: true },
	sort: { type: Object, required: true },
});
const emit = defineEmits(["sort"]);
</script>

<template>
	<ListHeader>
		<template v-for="column in columns" :key="column.field">
			<ListHeaderCell v-if="column.unsorted" :class="column.field === 'assigned_to' && 'pl-6'">
				{{ column.label() }}
			</ListHeaderCell>
			<ListHeaderCellSort
				v-else
				:direction="sort.field === column.field ? sort.dir : null"
				:align="column.align"
				@click="emit('sort', column.field)"
			>
				{{ column.label() }}
			</ListHeaderCellSort>
		</template>
	</ListHeader>
</template>
