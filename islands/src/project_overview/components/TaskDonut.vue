<script setup>
import { computed } from "vue";
import { ChartCard, DonutChart } from "frappe-ui/charts";

import { OTHER_STATUS, OUTCOME_COLORS, STATUS_COLORS } from "../colors.js";
import { useFormat } from "../format.js";
import { useActions } from "../host.js";

const props = defineProps({
	breakdown: { type: Object, default: null },
	delivery: { type: Boolean, default: false },
});

const __ = window.__;
const format = useFormat();
const actions = useActions();

// written out so the server's outcome labels are picked up for translation
const OUTCOME_LABELS = {
	"On Time": __("On Time"),
	Late: __("Late"),
	"No Due Date": __("No Due Date"),
	"Still Open": __("Still Open"),
	Cancelled: __("Cancelled"),
};

const slices = computed(() =>
	!props.breakdown
		? []
		: props.delivery
		? props.breakdown.outcomes.map(({ outcome, count, tasks }) => ({
				label: OUTCOME_LABELS[outcome],
				value: count,
				tasks,
				color: OUTCOME_COLORS[outcome],
		  }))
		: props.breakdown.statuses.map(({ status, count, tasks }) => ({
				label: __(status),
				value: count,
				tasks,
				color: STATUS_COLORS[status] || OTHER_STATUS,
		  }))
);
const colors = computed(() => Object.fromEntries(slices.value.map((slice) => [slice.label, slice.color])));

const count = (value) => format.number(value);
const open = ({ rows }) => rows[0] && actions.open_list("Task", { name: ["in", rows[0].tasks] });
</script>

<template>
	<ChartCard class="h-[350px]">
		<DonutChart
			:title="delivery ? __('Tasks by Outcome') : __('Tasks by Status')"
			:error="breakdown ? null : __('Could not load tasks')"
			:data="slices"
			category="label"
			value="value"
			order="rows"
			:colors="colors"
			:max-slices="Math.max(slices.length, 1)"
			:center-label="__('tasks')"
			:format="count"
			@select="open"
		>
			<template #error>
				<span class="text-sm-medium text-ink-red-7">{{ __("Could not load tasks") }}</span>
			</template>
		</DonutChart>
	</ChartCard>
</template>
