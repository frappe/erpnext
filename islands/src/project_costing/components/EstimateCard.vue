<script setup>
import { computed } from "vue";
import { Badge, Button, Progress, Tooltip } from "frappe-ui";
import { ChartCard, ChartContainer } from "frappe-ui/charts";

import FigureRows from "./FigureRows.vue";
import { useFormat } from "../format.js";

const props = defineProps({
	view: { type: Object, required: true },
	// Whether the user may set the estimate, which the Project form saves.
	can_set_estimate: { type: Boolean, default: false },
});
defineEmits(["set-estimate"]);

const __ = window.__;
const format = useFormat();
const source = __("Estimated Cost field on the Details tab");

const HEALTH = {
	ok: { label: __("Within estimate"), theme: "green" },
	risk: { label: __("Likely to go over"), theme: "amber" },
	over: { label: __("Over estimate"), theme: "red" },
	empty: { label: __("No costs yet"), theme: "gray" },
};

const badge = computed(() => {
	const view = props.view;
	if (view.phase === "completed") return { label: __("Completed"), theme: "gray" };
	if (view.phase === "cancelled") return { label: __("Cancelled"), theme: "gray" };
	return HEALTH[view.health];
});

// Cost to date is on the card above, so the rows show only the estimate and what is left of it.
const rows = computed(() => {
	const view = props.view;
	if (!view.has_estimate) return [];
	const over = view.cost > view.estimate;
	return [
		{ label: __("Estimated cost"), value: format.money(view.estimate) },
		over
			? { label: __("Over by"), value: format.money(view.cost - view.estimate), tone: "text-ink-red-5" }
			: {
					label: view.closed ? __("Unspent") : __("Remaining"),
					value: format.money(view.estimate - view.cost),
			  },
	];
});
</script>

<template>
	<ChartCard>
		<ChartContainer :title="__('Spend tracking')">
			<template #title-suffix>
				<Tooltip :text="source">
					<span class="lucide-info size-[1em] text-ink-gray-4" role="img" :aria-label="source" />
				</Tooltip>
			</template>
			<template v-if="view.has_estimate" #actions>
				<Badge :label="badge.label" :theme="badge.theme" variant="subtle" />
			</template>

			<div
				v-if="!view.has_estimate"
				class="flex h-full flex-col items-center justify-center gap-3 py-10 text-center"
			>
				<div class="rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
					<span class="lucide-calculator size-6" aria-hidden="true" />
				</div>
				<p class="text-base text-ink-gray-7">{{ __("No estimated cost") }}</p>
				<Button
					v-if="can_set_estimate"
					:label="__('Set estimate')"
					class="mt-2"
					@click="$emit('set-estimate')"
				/>
			</div>
			<div v-else class="space-y-4 pt-2">
				<Progress
					:value="Math.min(view.used_percent, 100)"
					:label="__('Estimated cost used · {0}', [format.percent(view.used_percent)])"
					size="md"
				/>
				<Progress
					v-if="!view.closed"
					:value="view.percent_complete"
					:label="__('Work complete · {0}', [format.percent(view.percent_complete)])"
					size="md"
				/>
				<FigureRows :rows="rows" />
			</div>
		</ChartContainer>
	</ChartCard>
</template>
