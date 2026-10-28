<script setup>
import { computed } from "vue";
import { Tooltip } from "frappe-ui";
import { ChartCard, ChartContainer } from "frappe-ui/charts";

import FigureRows from "./FigureRows.vue";
import { useFormat } from "../format.js";

const props = defineProps({
	view: { type: Object, required: true },
});

const __ = window.__;
const format = useFormat();

const rows = computed(() => {
	const view = props.view;
	if (view.phase === "cancelled") return [margin_row(__("Net result"), __("Billed − cost incurred"))];
	if (view.phase === "completed")
		return [margin_row(__("Final gross margin"), __("Billed − final cost")), ...planned_row()];
	if (!view.has_contract) return [margin_row(__("Gross margin to date"), __("Billed − cost to date"))];
	return [
		margin_row(__("Gross margin to date"), __("Billed − cost to date")),
		{
			label: __("Projected at completion"),
			caption: view.billing?.over_billed
				? __("Billed − forecast cost")
				: __("Contract − forecast cost"),
			value: view.projected_margin,
		},
		...planned_row(),
	];
});

function margin_row(label, caption) {
	return { label, caption, value: props.view.margin };
}

function planned_row() {
	const view = props.view;
	if (view.planned_margin == null) return [];
	return [
		{
			label: __("Planned"),
			caption: __("Contract − estimated cost"),
			value: view.planned_margin,
		},
	];
}

// The rows as figures: the amount, red when negative. What each row measures is in the tooltip
// by the title, not under every row.
const figures = computed(() =>
	rows.value.map((row) => ({
		label: row.label,
		value: format.short(row.value),
		tone: row.value < 0 ? "text-ink-red-5" : "text-ink-gray-9",
	}))
);

const formula = computed(() => rows.value.map((row) => `${row.label}: ${row.caption}`).join(" · "));
</script>

<template>
	<ChartCard>
		<ChartContainer :title="__('Margin')">
			<template #title-suffix>
				<Tooltip :text="formula">
					<span class="lucide-info size-[1em] text-ink-gray-4" role="img" :aria-label="formula" />
				</Tooltip>
			</template>
			<div class="pt-2">
				<FigureRows :rows="figures" />
			</div>
		</ChartContainer>
	</ChartCard>
</template>
