<script setup>
import { computed, ref } from "vue";
import { TabButtons, Tooltip } from "frappe-ui";
import { BarChart, ChartCard } from "frappe-ui/charts";

import { LABOUR_DRIVERS, driverRows } from "../costing.js";
import { useFormat } from "../format.js";

const props = defineProps({
	view: { type: Object, required: true },
});

const __ = window.__;
const format = useFormat();

// What each tab lists, and the text for a row with no name.
const DIMENSIONS = {
	activities: { label: __("Activity"), unnamed: __("No activity type") },
	employees: { label: __("Employee"), unnamed: __("No employee") },
	suppliers: { label: __("Supplier") },
	items: { label: __("Item") },
};

// A tab shows only when it has something to draw: the user may read its documents, which the
// server marks with null otherwise, and the project has rows for it.
const tabs = computed(() =>
	Object.entries(DIMENSIONS)
		.filter(([key]) => driverRows(props.view, key).length)
		.map(([key, dimension]) => ({ value: key, label: dimension.label }))
);
// Activities first; a user who may not read timesheets starts on the first tab they have.
const selected = ref("activities");
const tab = computed({
	get: () =>
		tabs.value.some((option) => option.value === selected.value) ? selected.value : tabs.value[0]?.value,
	set: (value) => (selected.value = value),
});

// Labour by person or activity reveals costing rates, so without them it shows hours.
const hours_only = computed(() => LABOUR_DRIVERS.includes(tab.value) && !props.view.access.labour);
const measure = computed(() => (hours_only.value ? "hours" : "amount"));

const rows = computed(() =>
	driverRows(props.view, tab.value).map((row) => ({
		...row,
		name: row.label || row.name || DIMENSIONS[tab.value].unnamed,
	}))
);

// Hours or invoice counts ride along in the tooltip, in their own unit.
const tooltip_columns = computed(() => {
	if (LABOUR_DRIVERS.includes(tab.value) && !hours_only.value)
		return [{ name: "hours", label: __("Hours"), format: format.number }];
	if (tab.value === "suppliers") return [{ name: "documents", label: __("Invoices") }];
	return [];
});

const value_format = (value) =>
	hours_only.value ? __("{0} h", [format.number(value)]) : format.short(value);
</script>

<template>
	<ChartCard class="h-96">
		<BarChart
			:key="`${tab}-${measure}`"
			:title="__('Top cost drivers')"
			:data="rows"
			x="name"
			:y="measure"
			horizontal
			:series-config="{ [measure]: { label: hours_only ? __('Hours') : __('Cost') } }"
			:tooltip-columns="tooltip_columns"
			:y-axis="{ format: value_format, min: 0 }"
		>
			<template v-if="hours_only" #title-suffix>
				<Tooltip :text="__('Hours only: amounts need access to costing rates')">
					<span
						class="lucide-info size-[1em] text-ink-gray-4"
						role="img"
						:aria-label="__('Hours only: amounts need access to costing rates')"
					/>
				</Tooltip>
			</template>
			<template #actions>
				<TabButtons v-model="tab" :options="tabs" size="sm" />
			</template>
		</BarChart>
	</ChartCard>
</template>
