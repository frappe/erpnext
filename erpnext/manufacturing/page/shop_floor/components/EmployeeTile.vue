<script setup>
import { computed } from "vue";
import { Avatar, Badge } from "frappe-ui";
import { __ } from "../lib/api";

const props = defineProps({ employee: Object, selected: Boolean, selectable: Boolean, assigned: Boolean });
defineEmits(["pick"]);

const meta = computed(() => {
	const row = props.employee;
	if (row.working_on) return __("Working on {0}", [row.working_on]);
	if (!row.job_cards?.length) return row.designation || __("No job cards assigned");
	const operations = [...new Set(row.job_cards.map((card) => card.operation))].join(", ");
	const count = row.job_cards.length === 1 ? __("1 job card") : __("{0} job cards", [row.job_cards.length]);
	return `${operations} · ${count}`;
});
</script>

<template>
	<button
		type="button"
		class="flex w-full items-center gap-3 rounded-5 border p-3 text-left transition-colors"
		:class="
			selected
				? 'border-outline-gray-5 bg-surface-gray-2'
				: 'border-outline-gray-2 bg-surface-base hover:bg-surface-gray-1'
		"
		:aria-pressed="selectable ? selected : undefined"
		@click="$emit('pick', employee)"
	>
		<Avatar :label="employee.employee_name" :image="employee.image" size="2xl" />
		<div class="min-w-0 flex-1">
			<p class="truncate text-lg font-semibold text-ink-gray-8">{{ employee.employee_name }}</p>
			<p class="truncate text-sm tabular-nums text-ink-gray-5">{{ employee.name }}</p>
			<p class="mt-0.5 truncate text-sm text-ink-gray-6">{{ meta }}</p>
		</div>
		<div class="flex shrink-0 flex-col items-end gap-1.5">
			<span
				v-if="selectable"
				class="size-5"
				:class="selected ? 'lucide-circle-check text-ink-gray-9' : 'lucide-circle text-ink-gray-4'"
				aria-hidden="true"
			/>
			<Badge v-if="assigned" :label="__('Assigned')" theme="blue" variant="subtle" />
			<Badge v-else-if="employee.working_on" :label="__('Busy')" theme="amber" variant="subtle" />
		</div>
	</button>
</template>
