<script setup>
import { Badge } from "frappe-ui";
import { __ } from "../../lib/api";
import { phaseOf, progressText } from "../../lib/status";

defineProps({ jobCards: Array, title: String, empty: String });
</script>

<template>
	<section class="space-y-2">
		<h3 class="text-base font-semibold text-ink-gray-8">{{ title }}</h3>
		<div
			v-if="jobCards.length"
			class="divide-y divide-outline-gray-1 rounded-5 border border-outline-gray-2"
		>
			<div v-for="row in jobCards" :key="row.name" class="space-y-1 px-4 py-3">
				<div class="flex items-center gap-2">
					<p class="min-w-0 flex-1 truncate text-base text-ink-gray-8">
						{{ row.operation }} · {{ row.item_name || row.production_item }}
					</p>
					<Badge
						v-if="row.phase"
						:label="phaseOf(row).label"
						:theme="phaseOf(row).theme"
						variant="subtle"
					/>
				</div>
				<p class="truncate text-sm tabular-nums text-ink-gray-5">
					{{ row.name }} · {{ row.work_order }}
				</p>
				<p class="truncate text-sm text-ink-gray-6">{{ progressText(row) }}</p>
			</div>
		</div>
		<p
			v-else
			class="rounded-5 border border-dashed border-outline-gray-2 px-4 py-6 text-center text-sm text-ink-gray-5"
		>
			{{ empty || __("Nothing here") }}
		</p>
	</section>
</template>
