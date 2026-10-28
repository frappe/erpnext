<script setup>
import { computed, ref } from "vue";
import { Button, Dialog, TabButtons, Tooltip } from "frappe-ui";
import { BarChart, ChartCard, LineChart } from "frappe-ui/charts";

import MonthlyTable from "./MonthlyTable.vue";
import { useFormat } from "../format.js";

const props = defineProps({
	view: { type: Object, required: true },
});

const __ = window.__;
const format = useFormat();

// The forecast line runs to the expected end date, but no further than this.
const FORECAST_MONTHS_LIMIT = 36;

const mode = ref("cumulative");
const modes = [
	{ value: "cumulative", label: __("Cumulative") },
	{ value: "monthly", label: __("By month") },
];
const show_table = ref(false);

const monthly = computed(() =>
	props.view.months.map((row) => {
		const total = props.view.sources.reduce((sum, source) => sum + (row[source.key] || 0), 0);
		return { ...row, label: format.month(row.month), total, billed_point: row.billed || null };
	})
);

const cumulative = computed(() => {
	let running = 0;
	const rows = monthly.value.map((row) => ({
		month: row.month,
		label: row.label,
		cost: (running += row.total),
	}));
	return with_forecast(rows);
});

/**
 * A dashed line from the cost to date to the forecast, at the expected end date. Only while the
 * project runs, and only when the end date lies after the last month with cost.
 */
function with_forecast(rows) {
	const view = props.view;
	const end = view.expected_end_date?.slice(0, 7);
	const last = rows.at(-1);
	if (view.closed || !view.percent_complete || !end || !last || end <= last.month) return rows;

	const ahead = [];
	for (let month = next_month(last.month); month <= end; month = next_month(month)) {
		if (ahead.length === FORECAST_MONTHS_LIMIT) break;
		ahead.push({ month, label: format.month(month), cost: null });
	}
	const step = (view.forecast - last.cost) / ahead.length;
	last.forecast = last.cost;
	ahead.forEach((row, index) => (row.forecast = last.cost + step * (index + 1)));
	return [...rows, ...ahead];
}

function next_month(key) {
	const [year, month] = key.split("-").map(Number);
	return month === 12 ? `${year + 1}-01` : `${year}-${String(month + 1).padStart(2, "0")}`;
}

const reference_lines = computed(() =>
	props.view.has_estimate
		? [
				{
					value: props.view.estimate,
					label: __("Estimate {0}", [format.short(props.view.estimate)]),
					dashed: true,
					labelPlacement: "start-top",
				},
		  ]
		: []
);

// Keep the estimate line inside the plot even when cost stays under it.
const y_max = computed(() => {
	const top = Math.max(
		props.view.estimate || 0,
		...cumulative.value.map((row) => row.forecast ?? row.cost)
	);
	return top ? top * 1.1 : undefined;
});

// Billing comes in milestones, so it shows as points on the months an invoice went out.
const chart = computed(() => {
	if (mode.value === "cumulative")
		return {
			is: LineChart,
			data: cumulative.value,
			y: cumulative.value.some((row) => row.forecast != null) ? ["cost", "forecast"] : ["cost"],
			seriesConfig: {
				cost: { label: __("Cost to date") },
				forecast: { label: __("Forecast"), dashed: true },
			},
			referenceLines: reference_lines.value,
			yAxis: { format: format.short, min: 0, max: y_max.value },
		};
	return {
		is: BarChart,
		data: monthly.value,
		y: props.view.internal ? ["total"] : ["total", "billed_point"],
		seriesConfig: {
			total: { label: __("Cost") },
			billed_point: { label: __("Billed"), type: "line", showDataPoints: true, connectNulls: false },
		},
		yAxis: { format: format.short, min: 0 },
	};
});

const subtitle = computed(() => {
	if (mode.value === "monthly")
		return props.view.internal ? __("Cost each month") : __("Cost each month, billing as points");
	return props.view.closed ? __("Cumulative, to the end") : __("Cumulative, with forecast");
});
</script>

<template>
	<ChartCard class="h-96">
		<component
			:is="chart.is"
			:key="mode"
			:title="__('Cost over time')"
			:subtitle="subtitle"
			:data="chart.data"
			x="label"
			:y="chart.y"
			:series-config="chart.seriesConfig"
			:reference-lines="chart.referenceLines"
			:y-axis="chart.yAxis"
		>
			<template #actions>
				<div class="flex items-center gap-2">
					<TabButtons v-model="mode" :options="modes" size="sm" />
					<Tooltip :text="__('View by month')">
						<Button
							size="sm"
							variant="ghost"
							icon="lucide-table"
							:aria-label="__('View by month')"
							@click="show_table = true"
						/>
					</Tooltip>
				</div>
			</template>
		</component>

		<Dialog v-model:open="show_table" :title="__('Cost by month')" size="4xl">
			<MonthlyTable :view="view" :months="monthly" />
		</Dialog>
	</ChartCard>
</template>
