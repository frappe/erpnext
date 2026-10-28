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

const SUBTITLES = {
	completed: __("Final cost against the estimate"),
	cancelled: __("Spent against the estimate"),
};

const badge = computed(() => {
	const view = props.view;
	if (view.phase === "completed") return { label: __("Completed"), theme: "gray" };
	if (view.phase === "cancelled") return { label: __("Cancelled"), theme: "gray" };
	return HEALTH[view.health];
});

const verdict = computed(() => {
	const view = props.view;
	if (view.phase === "completed")
		return view.variance > 0
			? __("Finished {0} over the estimate.", [format.short(view.variance)])
			: __("Finished {0} under the estimate.", [format.short(-view.variance)]);
	if (view.phase === "cancelled")
		return view.cost > view.estimate
			? __("Spent {0} more than the estimate before cancelling.", [
					format.short(view.cost - view.estimate),
			  ])
			: __("{0} of the estimate was never spent.", [format.short(view.estimate - view.cost)]);
	const pace = spending_pace(view);
	// on hold the project still runs, so the forecast stands, on one assumption
	return view.phase === "hold"
		? `${pace} ${__("On hold: the forecast assumes work resumes at the same pace.")}`
		: pace;
});

function spending_pace(view) {
	const gap = Math.round(view.used_percent - view.percent_complete);
	if (Math.abs(gap) <= 3) return __("Spending is in line with progress.");
	return gap > 0
		? __("Spending is {0} points ahead of progress.", [gap])
		: __("Spending is {0} points behind progress.", [-gap]);
}

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
		<ChartContainer
			:title="__('Budget')"
			:subtitle="SUBTITLES[view.phase] || __('Against the estimated cost')"
		>
			<template #actions>
				<Badge :label="badge.label" :theme="badge.theme" variant="subtle" />
			</template>

			<div class="space-y-4 pt-2">
				<p v-if="!view.has_estimate" class="text-p-sm text-ink-gray-6">
					{{
						view.closed
							? __("No estimated cost was set while the project ran.")
							: __(
									"No estimated cost. Set Estimated Cost on the Details tab to see how much of the budget is used."
							  )
					}}
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
					<p class="text-p-sm text-ink-gray-6">{{ verdict }}</p>
				</template>
				<FigureRows :rows="rows" />
			</div>
		</ChartContainer>
	</ChartCard>
</template>
