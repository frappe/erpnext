<script setup>
import { computed } from "vue";
import { Avatar, Badge, Progress } from "frappe-ui";
import { __, go } from "../lib/api";
import { STATION_THEME, stationSummary } from "../lib/status";

const props = defineProps({ workstation: Object, mine: Boolean });

const job = computed(() => props.workstation.current);
const summary = computed(() => stationSummary(props.workstation));
const frame = computed(() => {
	if (props.workstation.status === "Problem") return "border-outline-red-3 bg-surface-red-1";
	return props.mine ? "border-outline-gray-5 bg-surface-base" : "border-outline-gray-2 bg-surface-base";
});
</script>

<template>
	<button
		type="button"
		class="flex min-h-36 w-full flex-col gap-3 rounded-5 border p-4 text-left shadow-sm transition-colors hover:bg-surface-gray-1"
		:class="frame"
		@click="go('station', workstation.name)"
	>
		<div class="flex w-full items-start gap-3">
			<div class="min-w-0 flex-1">
				<p class="truncate text-lg font-semibold text-ink-gray-8">{{ workstation.name }}</p>
				<p class="truncate text-sm text-ink-gray-5">
					{{ workstation.workstation_type || __("Workstation") }}
				</p>
			</div>
			<Badge
				:label="__(workstation.status)"
				:theme="STATION_THEME[workstation.status] || 'gray'"
				variant="subtle"
				size="lg"
			/>
		</div>
		<div class="w-full min-w-0">
			<p class="truncate text-base text-ink-gray-8">
				{{ job ? job.item_name || job.production_item : "" }}
			</p>
			<p class="truncate text-sm" :class="summary.tone">{{ summary.text }}</p>
		</div>
		<Progress
			v-if="job && job.for_quantity"
			class="w-full"
			:value="(job.total_completed_qty / job.for_quantity) * 100"
			size="sm"
		/>
		<div class="mt-auto flex w-full items-center gap-2 text-sm text-ink-gray-5">
			<div v-if="job?.crew.length" class="flex -space-x-1.5">
				<Avatar v-for="id in job.crew" :key="id" :label="job.names[id] || id" size="sm" />
			</div>
			<span class="ml-auto shrink-0 tabular-nums">{{
				__("{0} in queue", [workstation.queue_count])
			}}</span>
		</div>
	</button>
</template>
