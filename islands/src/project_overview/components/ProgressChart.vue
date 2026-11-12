<script setup>
import { computed } from "vue";
import { ChartCard, ChartContainer, LineChart } from "frappe-ui/charts";

import InfoTip from "./InfoTip.vue";
import { useFormat } from "../format.js";
import { useActions } from "../host.js";

const BEHIND_PLAN_WARNING = 5;

const props = defineProps({
	chart: { type: Object, default: null },
	delivery: { type: Object, default: null },
});

const __ = window.__;
const moment = window.moment;
const format = useFormat();
const actions = useActions();

const title = computed(() =>
	props.chart && !props.chart.has_plan ? __("Completed over Time") : __("Planned vs Completed")
);

const date_text = (date) => {
	const { points } = props.chart;
	const spans_years = moment(points[0].date).year() !== moment(points.at(-1).date).year();
	return moment(date).format(spans_years ? "D MMM YY" : "D MMM");
};

const rows = computed(() =>
	props.chart.points.map((point) => ({
		label: date_text(point.date),
		planned: point.planned,
		completed: point.completed,
	}))
);

const series = computed(() => (props.chart.has_plan ? ["planned", "completed"] : ["completed"]));
const series_config = {
	planned: { label: __("Planned"), dashed: true, color: "var(--surface-gray-5)" },
	completed: { label: __("Completed"), type: "area", color: "var(--surface-green-7)" },
};

const reference_lines = computed(() => {
	const { today_index } = props.chart;
	return today_index == null
		? []
		: [{ value: rows.value[today_index].label, axis: "x", label: __("Today"), dashed: true }];
});

const about = computed(() => {
	const { method, points, has_plan, completed_without_date } = props.chart;
	const measure = {
		"Task Completion": __("Cumulative % of tasks closed"),
		"Task Progress": __("Cumulative % of task progress"),
		"Task Weight": __("Cumulative % of task weight"),
	}[method];
	const weeks = points.length > 1 ? moment(points[1].date).diff(points[0].date, "weeks") : 1;
	const lines = [measure + ", " + (weeks > 1 ? __("every {0} weeks", [weeks]) : __("by week"))];
	if (has_plan) lines.push(__("Planned by Expected End Date"));
	lines.push(__("Completed by Completed On"));
	if (completed_without_date) {
		lines.push(__("{0} without Completed On use their last change", [completed_without_date]));
	}
	return lines.join("\n");
});

const subtitle = computed(() => (props.delivery ? delivery_subtitle(props.delivery) : open_subtitle()));

function open_subtitle() {
	const { points, has_plan, today_index, undated, total } = props.chart;
	const latest = Math.max(
		points.findLastIndex((point) => point.completed != null),
		0
	);
	const point = points[today_index ?? latest];
	const completed = format.percent(point.completed || 0);
	if (!has_plan) {
		return [
			{ text: __("{0} done", [completed]) + " · " },
			{ link: __("{0} of {1} tasks need a due date", [undated, total]) },
		];
	}
	const planned = format.percent(point.planned || 0);
	return [{ text: __("{0} done of {1} planned", [completed, planned]) + " · " }, gap_part(point)];
}

function gap_part({ planned, completed }) {
	const gap = Math.round((completed || 0) - (planned || 0));
	if (!gap) return { gap: __("On plan") };
	if (gap > 0) return { gap: __("{0} pts ahead", [gap]), tone: "text-ink-green-7" };
	return {
		gap: __("{0} pts behind", [-gap]),
		tone: -gap > BEHIND_PLAN_WARNING ? "text-ink-amber-7" : "text-ink-gray-7",
	};
}

function delivery_subtitle({ days_late, finished_on }) {
	const parts = [];
	if (days_late > 0) {
		parts.push(
			days_late === 1
				? __("Finished 1 day after plan")
				: __("Finished {0} days after plan", [days_late])
		);
	} else if (days_late < 0) {
		parts.push(
			days_late === -1
				? __("Finished 1 day ahead of plan")
				: __("Finished {0} days ahead of plan", [-days_late])
		);
	} else if (days_late === 0) {
		parts.push(__("Finished on plan"));
	} else if (finished_on) {
		parts.push(__("Finished {0}", [moment(finished_on).format("D MMM YYYY")]));
	}

	const { has_plan, undated, total, worst_gap } = props.chart;
	if (!has_plan) {
		parts.push(__("No plan: {0} of {1} tasks have no Expected End Date", [undated, total]));
		return [{ text: parts.join(" · ") }];
	}
	if (!worst_gap) return [{ text: parts.join(" · ") }];

	const lead = { text: parts.length ? parts.join(" · ") + " · " : "" };
	const gap = Math.round(worst_gap.points);
	if (gap <= 0) return [lead, { gap: __("Never behind plan"), tone: "text-ink-green-7" }];
	return [
		lead,
		{
			gap: __("At most {0} pts behind, on {1}", [gap, moment(worst_gap.date).format("D MMM")]),
			tone: gap > BEHIND_PLAN_WARNING ? "text-ink-amber-7" : "text-ink-gray-7",
		},
	];
}

const open_undated = () => actions.open_task_list({ exp_end_date: ["is", "not set"] });
</script>

<template>
	<ChartCard class="h-[350px]">
		<ChartContainer :title="title" :error="chart ? null : __('Could not load tasks')">
			<template v-if="chart" #title-suffix><InfoTip :text="about" /></template>
			<template #error>
				<span class="text-sm-medium text-ink-red-7">{{ __("Could not load tasks") }}</span>
			</template>

			<div v-if="chart" class="flex h-full flex-col gap-1">
				<!-- ChartContainer's subtitle is plain text, and this one has a link -->
				<div class="-mt-1 text-sm text-ink-gray-5">
					<template v-for="(part, index) in subtitle" :key="index">
						<span v-if="part.text">{{ part.text }}</span>
						<button
							v-else-if="part.link"
							type="button"
							class="text-ink-gray-7 underline decoration-outline-gray-3 underline-offset-2 hover:text-ink-gray-9"
							@click="open_undated"
						>
							{{ part.link }}
						</button>
						<span v-else-if="part.gap" class="font-medium" :class="part.tone">{{
							part.gap
						}}</span>
					</template>
				</div>
				<div class="min-h-0 flex-1">
					<LineChart
						:data="rows"
						x="label"
						:y="series"
						:series-config="series_config"
						:reference-lines="reference_lines"
						:y-axis="{ min: 0, max: 100, format: format.percent }"
						:x-axis="{ type: 'category' }"
					/>
				</div>
			</div>
		</ChartContainer>
	</ChartCard>
</template>
