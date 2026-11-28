<script setup>
import { computed } from "vue";
import { Avatar, Badge, Progress, Tooltip } from "frappe-ui";
import { __ } from "../lib/api";
import { phaseOf, progressText } from "../lib/status";
import { fmt } from "../lib/format";

const props = defineProps({ jobCard: Object });

const phase = computed(() => phaseOf(props.jobCard));
const note = computed(() => {
	const row = props.jobCard;
	const loss = row.process_loss_qty ? ` · ${__("{0} lost", [fmt(row.process_loss_qty)])}` : "";
	return progressText(row) + loss;
});
</script>

<template>
	<div class="flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3">
		<div class="min-w-0 flex-1 basis-72">
			<p class="truncate text-lg text-ink-gray-8">
				{{ jobCard.operation }} · {{ jobCard.item_name || jobCard.production_item }}
			</p>
			<p class="truncate text-sm tabular-nums text-ink-gray-5">
				{{ jobCard.name }} · {{ jobCard.work_order }} · {{ jobCard.workstation }}
			</p>
			<p class="truncate text-sm text-ink-gray-6">{{ note }}</p>
			<Progress
				v-if="jobCard.for_quantity"
				:value="(jobCard.total_completed_qty / jobCard.for_quantity) * 100"
				size="sm"
				class="mt-2 max-w-sm"
			/>
		</div>
		<div class="flex w-32 items-center">
			<div v-if="jobCard.assigned.length" class="flex -space-x-1.5">
				<Tooltip v-for="id in jobCard.assigned" :key="id" :text="jobCard.names[id] || id">
					<Avatar :label="jobCard.names[id] || id" size="lg" />
				</Tooltip>
			</div>
			<Badge v-else :label="__('Unassigned')" theme="amber" variant="subtle" />
		</div>
		<div class="w-36"><Badge :label="phase.label" :theme="phase.theme" variant="subtle" size="lg" /></div>
		<slot />
	</div>
</template>
