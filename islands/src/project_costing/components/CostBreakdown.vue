<script setup>
import { computed, ref } from "vue";
import { TabButtons, Tooltip, toast } from "frappe-ui";
import { BarChart, ChartCard, DonutChart } from "frappe-ui/charts";
import { useHost } from "@framework/ui/island";

import { useFormat } from "../format.js";

const props = defineProps({
	view: { type: Object, required: true },
});

const __ = window.__;
const format = useFormat();
const host = useHost();

const mode = ref("total");
const modes = [
	{ value: "total", label: __("Total") },
	{ value: "monthly", label: __("By month") },
];

const active = computed(() => props.view.sources.filter((source) => source.amount > 0));
const slices = computed(() => active.value.map((source) => ({ label: source.label, amount: source.amount })));
const months = computed(() => props.view.months.map((row) => ({ ...row, label: format.month(row.month) })));
const series = computed(() =>
	Object.fromEntries(active.value.map((source) => [source.key, { label: source.label }]))
);

// Where each slice comes from, behind the info mark by the title.
const notes = computed(() =>
	active.value.map((source) => __("{0}: {1}", [source.label, source.via])).join(" · ")
);

// Totals show to everyone; the entries behind a slice open only for those who can read them.
function open_source(event) {
	const source = active.value.find((row) => row.label === event?.name);
	if (!source) return;
	if (source.access && !props.view.access[source.access]) {
		toast.info(__("You don't have access to the entries behind {0}", [source.label]));
		return;
	}
	host.navigate?.(source.route(props.view.project));
}
</script>

<template>
	<ChartCard class="h-96">
		<DonutChart
			v-if="mode === 'total'"
			:title="__('Cost by source')"
			:data="slices"
			category="label"
			value="amount"
			:format="format.short"
			:center-label="__('Total cost')"
			@select="open_source"
		>
			<template #title-suffix>
				<Tooltip :text="notes">
					<span class="lucide-info size-[1em] text-ink-gray-4" role="img" :aria-label="notes" />
				</Tooltip>
			</template>
			<template #actions>
				<TabButtons v-model="mode" :options="modes" size="sm" />
			</template>
		</DonutChart>
		<BarChart
			v-else
			:title="__('Cost by source')"
			:data="months"
			x="label"
			:y="active.map((source) => source.key)"
			stacked
			:series-config="series"
			:y-axis="{ format: format.short, min: 0 }"
		>
			<template #actions>
				<TabButtons v-model="mode" :options="modes" size="sm" />
			</template>
		</BarChart>
	</ChartCard>
</template>
