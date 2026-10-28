<script setup>
import { computed } from "vue";
import { List, ListCell, ListHeader, ListHeaderCell, ListRow } from "frappe-ui/list";

import { useFormat } from "../format.js";

const props = defineProps({
	view: { type: Object, required: true },
	// The view's months, each with its label and total cost.
	months: { type: Array, required: true },
});

const __ = window.__;
const format = useFormat();

const sources = computed(() => props.view.sources.filter((source) => source.amount));

const columns = computed(() => [
	"4.5rem",
	...sources.value.map(() => "minmax(5rem,1fr)"),
	"minmax(5.5rem,1fr)",
	...(props.view.internal ? [] : ["minmax(5.5rem,1fr)", "minmax(5.5rem,1fr)"]),
]);

const rows = computed(() => {
	const view = props.view;
	const total = {
		month: "total",
		label: __("Total"),
		total: view.cost,
		billed: view.billed,
		is_total: true,
	};
	sources.value.forEach((source) => (total[source.key] = source.amount));
	return [...props.months, total].map((row) => ({ ...row, net: (row.billed || 0) - row.total }));
});

const amount = (value) => (value ? format.short(value) : "—");
</script>

<template>
	<div class="-mx-1 overflow-x-auto px-1">
		<div class="min-w-[720px]">
			<List :columns="columns" :row-height="40">
				<ListHeader>
					<ListHeaderCell>{{ __("Month") }}</ListHeaderCell>
					<ListHeaderCell v-for="source in sources" :key="source.key" class="justify-end">
						{{ source.label }}
					</ListHeaderCell>
					<ListHeaderCell class="justify-end">{{ __("Total cost") }}</ListHeaderCell>
					<template v-if="!view.internal">
						<ListHeaderCell class="justify-end">{{ __("Billed") }}</ListHeaderCell>
						<ListHeaderCell class="justify-end">{{ __("Net") }}</ListHeaderCell>
					</template>
				</ListHeader>
				<ListRow v-for="row in rows" :key="row.month">
					<ListCell>
						<span
							:class="
								row.is_total ? 'text-sm-semibold text-ink-gray-9' : 'text-sm text-ink-gray-7'
							"
						>
							{{ row.label }}
						</span>
					</ListCell>
					<ListCell v-for="source in sources" :key="source.key" class="justify-end">
						<span class="text-sm tabular-nums text-ink-gray-7">{{
							amount(row[source.key])
						}}</span>
					</ListCell>
					<ListCell class="justify-end">
						<span class="text-sm-semibold tabular-nums text-ink-gray-8">{{
							format.short(row.total)
						}}</span>
					</ListCell>
					<template v-if="!view.internal">
						<ListCell class="justify-end">
							<span class="text-sm tabular-nums text-ink-gray-7">{{ amount(row.billed) }}</span>
						</ListCell>
						<ListCell class="justify-end">
							<span
								class="text-sm tabular-nums"
								:class="row.net < 0 ? 'text-ink-red-5' : 'text-ink-green-5'"
							>
								{{ format.short(row.net) }}
							</span>
						</ListCell>
					</template>
				</ListRow>
			</List>
		</div>
	</div>
	<p v-if="!view.internal" class="mt-3 text-p-xs text-ink-gray-5">
		{{
			__(
				"Net swings month to month because billing follows milestones while cost is booked as work happens."
			)
		}}
	</p>
</template>
