<script setup>
import { computed } from "vue";
import { Badge, Progress } from "frappe-ui";
import { ChartCard, ChartContainer } from "frappe-ui/charts";

import FigureRows from "./FigureRows.vue";
import { useFormat } from "../format.js";

const props = defineProps({
	view: { type: Object, required: true },
});

const __ = window.__;
const format = useFormat();

const HEALTH = {
	ok: { label: __("Within budget"), theme: "green" },
	risk: { label: __("Trending over"), theme: "amber" },
	over: { label: __("Over budget"), theme: "red" },
	none: { label: __("No estimate"), theme: "gray" },
	empty: { label: __("No costs yet"), theme: "gray" },
};

const badge = computed(() => {
	const view = props.view;
	if (view.phase === "completed") return { label: __("Completed"), theme: "gray" };
	if (view.phase === "cancelled") return { label: __("Cancelled"), theme: "gray" };
	return HEALTH[view.health];
});

const rows = computed(() => {
	const view = props.view;
	const forecast = {
		label: __("Forecast at completion"),
		value: view.percent_complete > 0 ? format.short(view.forecast) : __("Needs % complete"),
		tone: view.health === "over" || view.health === "risk" ? "text-ink-red-5" : "",
	};
	if (!view.has_estimate) return [{ label: __("Cost to date"), value: format.short(view.cost) }, forecast];
	const over = view.cost > view.estimate;
	const out = [
		{ label: __("Estimated cost"), value: format.short(view.estimate) },
		{ label: view.closed ? __("Final cost") : __("Cost to date"), value: format.short(view.cost) },
		over
			? { label: __("Over by"), value: format.short(view.cost - view.estimate), tone: "text-ink-red-5" }
			: {
					label: view.closed ? __("Unspent") : __("Remaining"),
					value: format.short(view.estimate - view.cost),
			  },
	];
	return view.closed ? out : [...out, forecast];
});
</script>

<template>
	<ChartCard>
		<ChartContainer :title="__('Budget')">
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
						:label="__('Budget used · {0}', [format.percent(view.used_percent)])"
						size="md"
					/>
					<Progress
						v-if="!view.closed"
						:value="view.percent_complete"
						:label="__('Work complete · {0}', [format.percent(view.percent_complete)])"
						size="md"
					/>
				</template>
				<FigureRows :rows="rows" />
			</div>
		</ChartContainer>
	</ChartCard>
</template>
