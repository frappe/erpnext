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
	...sources.value.map(() => "minmax(6rem,1fr)"),
	"minmax(6.5rem,1fr)",
]);

const rows = computed(() => {
	const total = { month: "total", label: __("Total"), total: props.view.cost, is_total: true };
	sources.value.forEach((source) => (total[source.key] = source.amount));
	return [...props.months, total];
});

const amount = (value) => (value ? format.money(value) : "—");
</script>

<template>
	<div class="-mx-1 overflow-x-auto px-1">
		<div class="min-w-[560px]">
			<List :columns="columns" :row-height="40">
				<ListHeader>
					<ListHeaderCell>{{ __("Month") }}</ListHeaderCell>
					<ListHeaderCell v-for="source in sources" :key="source.key" class="justify-end">
						{{ source.label }}
					</ListHeaderCell>
					<ListHeaderCell class="justify-end">{{ __("Total cost") }}</ListHeaderCell>
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
							format.money(row.total)
						}}</span>
					</ListCell>
				</ListRow>
			</List>
		</div>
	</div>
</template>
