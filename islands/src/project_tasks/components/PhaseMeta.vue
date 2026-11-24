<script setup>
import { computed } from "vue";
import { Progress } from "frappe-ui";

import { short_date } from "../lib/dates.js";

// What a parent task's card shows next to its name: how far along its tasks are, and its dates.
const props = defineProps({
	phase: { type: Object, required: true },
	done: { type: Number, required: true },
	total: { type: Number, required: true },
});

const percent = computed(() => (props.total ? Math.round((props.done / props.total) * 100) : 0));
const range = computed(() => {
	const { exp_start_date: start, exp_end_date: end } = props.phase;
	if (start && end) return `${short_date(start)} – ${short_date(end)}`;
	return start || end ? short_date(start || end) : "";
});
</script>

<template>
	<span class="flex items-center gap-2">
		<span class="block w-16"><Progress :value="percent" size="sm" /></span>
		<span class="text-sm tabular-nums text-ink-gray-5">{{ done }}/{{ total }}</span>
	</span>
	<span v-if="range" class="text-sm tabular-nums text-ink-gray-5 max-sm:hidden">{{ range }}</span>
</template>
