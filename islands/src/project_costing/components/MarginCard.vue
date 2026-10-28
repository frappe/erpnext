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

const SUBTITLES = {
	cancelled: __("What was recovered against what was spent"),
	completed: __("How the project ended against the plan"),
};

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
				? __("Billed − forecast cost (billed is above the orders)")
				: __("Contract − forecast cost"),
			value: view.projected_margin,
			percent: view.projected_margin_percent,
		},
		...planned_row(),
	];
});

function margin_row(label, caption) {
	return { label, caption, value: props.view.margin, percent: props.view.margin_percent };
}

function planned_row() {
	const view = props.view;
	if (view.planned_margin == null) return [];
	return [
		{
			label: __("Planned"),
			caption: __("Contract − estimated cost"),
			value: view.planned_margin,
			percent: view.planned_margin_percent,
		},
	];
}

const note = computed(() => {
	const view = props.view;
	if (view.phase === "cancelled") return __("The project was cancelled, so there is no projected margin.");
	if (view.phase === "completed") return completed_note();
	if (!view.has_contract)
		return __(
			"No sales order, so there is no contract to project a margin from. Margin to date is billed against cost."
		);
	if (!view.has_estimate) return __("Set an estimated cost to compare against the planned margin.");
	const gap = Math.round(view.projected_margin_percent - view.planned_margin_percent);
	if (Math.abs(gap) <= 1) return __("Projected margin is in line with the plan.");
	return gap > 0
		? __("Projected margin is {0} points above the plan.", [gap])
		: __("Projected margin is {0} points below the plan.", [-gap]);
});

function completed_note() {
	const view = props.view;
	const parts = [];
	if (view.planned_margin != null) {
		const gap = view.margin - view.planned_margin;
		parts.push(
			gap >= 0
				? __("Finished {0} above the planned margin.", [format.short(gap)])
				: __("Finished {0} below the planned margin.", [format.short(-gap)])
		);
	}
	const never_billed = view.billing?.left_to_bill;
	if (never_billed > 0)
		parts.push(__("{0} of the contract was never billed.", [format.short(never_billed)]));
	return parts.join(" ") || __("Final figures.");
}

// The rows as figures: amount, its percent below, red when negative. What each row measures
// is in the tooltip by the title, not under every row.
const figures = computed(() =>
	rows.value.map((row) => ({
		label: row.label,
		value: format.short(row.value),
		detail: format.percent(row.percent, 1),
		tone: row.value < 0 ? "text-ink-red-5" : "text-ink-gray-9",
	}))
);

const formula = computed(() => {
	const name = props.view.phase === "cancelled" ? __("Net result") : __("Gross margin");
	const definitions = rows.value.map((row) => `${row.label}: ${row.caption}.`).join(" ");
	return `${definitions} ${name} = ${formula_terms.value}. ${__(
		"Calculated from the documents booked against this project."
	)}`;
});

const formula_terms = computed(() =>
	props.view.hrms
		? __("billed − (timesheet labour + non-stock purchases + materials consumed + expense claims)")
		: __("billed − (timesheet labour + non-stock purchases + materials consumed)")
);
</script>

<template>
	<ChartCard>
		<ChartContainer
			:title="__('Margin')"
			:subtitle="SUBTITLES[view.phase] || __('Margin to date moves with billing milestones')"
		>
			<template #title-suffix>
				<Tooltip :text="formula">
					<span class="lucide-info size-[1em] text-ink-gray-4" role="img" :aria-label="formula" />
				</Tooltip>
			</template>
			<div class="space-y-3 pt-2">
				<FigureRows :rows="figures" />
				<p class="text-p-sm text-ink-gray-6">{{ note }}</p>
			</div>
		</ChartContainer>
	</ChartCard>
</template>
