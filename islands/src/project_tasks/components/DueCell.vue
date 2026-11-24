<script setup>
import { computed } from "vue";
import { days_until, long_date, short_date } from "../lib/dates.js";

const props = defineProps({
	date: { type: String, default: null },
	// a hint only for work still to do
	open: { type: Boolean, default: false },
});

const __ = window.__;

// only a quiet hint for what is coming up; past dates show as they are
const hint = computed(() => {
	if (!props.date || !props.open) return null;
	const days = days_until(props.date);
	if (days === 0) return __("Today");
	if (days === 1) return __("In 1 day");
	if (days > 1 && days <= 7) return __("In {0} days", [days]);
	return null;
});
</script>

<template>
	<!-- no date: the cell stays blank. The full date is a native title: a long list has two
	     dates per row, too many for tooltip components. -->
	<span
		v-if="date"
		class="relative flex min-w-0 items-baseline gap-2 truncate text-ink-gray-7"
		:title="long_date(date)"
	>
		<span class="text-base tabular-nums">{{ short_date(date) }}</span>
		<span v-if="hint" class="text-sm max-lg:hidden">{{ hint }}</span>
	</span>
</template>
