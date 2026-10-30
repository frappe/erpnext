<script setup>
import { computed } from "vue";
import { Badge, Progress, Tooltip } from "frappe-ui";
import { ChartCard, ChartContainer } from "frappe-ui/charts";

import FigureRows from "./FigureRows.vue";
import { useFormat } from "../format.js";

const props = defineProps({
	view: { type: Object, required: true },
});

const __ = window.__;
const format = useFormat();
const source = __("Estimated Cost field on the Details tab");

const HEALTH = {
	ok: { label: __("Within estimate"), theme: "green" },
	risk: { label: __("Trending over"), theme: "amber" },
	over: { label: __("Over estimate"), theme: "red" },
	none: { label: __("No estimate"), theme: "gray" },
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
			<template #actions>
				<Badge :label="badge.label" :theme="badge.theme" variant="subtle" />
			</template>

			<div class="space-y-4 pt-2">
				<p v-if="!view.has_estimate && !view.closed" class="text-p-sm text-ink-gray-5">
					{{ __("Set Estimated Cost on the Details tab.") }}
				</p>
				<template v-else>
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
				</template>
				<FigureRows v-if="rows.length" :rows="rows" />
			</div>
		</ChartContainer>
	</ChartCard>
</template>
