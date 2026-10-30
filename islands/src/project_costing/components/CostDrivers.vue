<script setup>
import { computed, ref } from "vue";
import { TabButtons, Tooltip } from "frappe-ui";
import { BarChart, ChartCard } from "frappe-ui/charts";

import { useFormat } from "../format.js";

const props = defineProps({
	view: { type: Object, required: true },
});

const __ = window.__;
const format = useFormat();

// What each tab lists, the text for a row with no name, and the text when it is empty.
const DIMENSIONS = {
	activities: {
		label: __("Activity"),
		unnamed: __("No activity type"),
		empty: __("No timesheets against this project yet"),
	},
	employees: {
		label: __("Employee"),
		unnamed: __("No employee"),
		empty: __("No timesheets against this project yet"),
	},
	suppliers: { label: __("Supplier"), empty: __("No purchase invoices against this project yet") },
	items: { label: __("Item"), empty: __("No stock consumed against this project yet") },
};
const LABOUR = ["activities", "employees"];

const drivers = computed(() => props.view.drivers || {});

// A tab shows only when the user may read its documents, which the server marks with null.
const tabs = computed(() =>
	Object.entries(DIMENSIONS)
		.filter(([key]) => drivers.value[key] != null)
		.map(([key, dimension]) => ({ value: key, label: dimension.label }))
);
const tab = ref("activities");

// Labour by person or activity reveals costing rates, so without them it shows hours.
const hours_only = computed(() => LABOUR.includes(tab.value) && !props.view.access.labour);
const measure = computed(() => (hours_only.value ? "hours" : "amount"));

// In cost, an activity whose hours all lack a costing rate has nothing to draw, so it is left out
// rather than shown as an empty bar; the Cost to date card says how many hours that is.
const rows = computed(() =>
	(drivers.value[tab.value] || [])
		.filter((row) => hours_only.value || row.amount)
		.map((row) => ({
			...row,
			name: row.label || row.name || DIMENSIONS[tab.value].unnamed,
		}))
);

// Hours or invoice counts ride along in the tooltip, in their own unit.
const tooltip_columns = computed(() => {
	if (LABOUR.includes(tab.value) && !hours_only.value)
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
			<template #empty>
				<span class="text-sm text-ink-gray-5">{{ DIMENSIONS[tab].empty }}</span>
			</template>
		</BarChart>
	</ChartCard>
</template>
