<script setup>
import { computed, inject } from "vue";
import { TextInput } from "frappe-ui";
import { __ } from "../../lib/api";
import { fmt, num } from "../../lib/format";

const props = defineProps({ stage: Object, editable: Boolean });
const run = inject("run");
const tolerance = computed(() => num(run.state.value.plant.doc.formula_tolerance));

const key = (row) => row.name || row.item_code;
const sub = (row) => {
	if (row.is_balance_item) return __("Balance, tops the batch up");
	if (!row.is_input) return row.source_warehouse;
	return props.editable ? __("Waiting in {0}", [row.source_stage]) : __("From {0}", [row.source_stage]);
};
const canEdit = (row) => props.editable && !row.is_balance_item;
const planned = (row) => run.plannedOf(props.stage, row);
const isOff = (row) => {
	const actual = run.actualOf(props.stage, row);
	if (row.is_input) return actual > row.waiting_qty + 0.0001 && props.editable;
	if (row.is_balance_item || !planned(row)) return false;
	return Math.abs(((actual - planned(row)) / planned(row)) * 100) > tolerance.value + 0.0001;
};
function setActual(row, value) {
	if (row.is_input) run.setPass(props.stage, row, value);
	else run.local.actual[props.stage.idx][key(row)] = value;
}

defineExpose({ isOff });
</script>

<template>
	<div class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
		<div
			class="grid h-8 grid-cols-[minmax(0,1fr)_5.25rem_6rem] items-center gap-2 px-3 text-xs text-ink-gray-5"
		>
			<span>{{ __("Item") }}</span>
			<span class="text-right">{{ __("Planned") }}</span>
			<span class="text-right">{{ editable ? __("Actual") : __("Used") }}</span>
		</div>
		<div
			v-for="row in stage.items"
			:key="key(row)"
			class="grid h-12 grid-cols-[minmax(0,1fr)_5.25rem_6rem] items-center gap-2 px-3"
		>
			<div class="min-w-0">
				<p class="truncate text-sm text-ink-gray-8" :title="row.item_name">{{ row.item_name }}</p>
				<p class="truncate text-xs text-ink-gray-5">{{ sub(row) }}</p>
			</div>
			<span class="truncate whitespace-nowrap text-right text-sm tabular-nums text-ink-gray-6">
				{{ fmt(planned(row)) }} {{ row.uom }}
			</span>
			<TextInput
				v-if="canEdit(row)"
				:model-value="run.local.actual[stage.idx][key(row)]"
				@update:model-value="setActual(row, $event)"
				type="number"
				size="sm"
				class="[&_input]:bg-surface-base [&_input]:text-right"
				:class="isOff(row) ? '[&_input]:text-ink-red-5' : ''"
			/>
			<span
				v-else
				class="text-right text-sm tabular-nums"
				:class="isOff(row) ? 'text-ink-red-5' : 'text-ink-gray-8'"
			>
				{{ fmt(run.actualOf(stage, row)) }}
			</span>
		</div>
	</div>
</template>
