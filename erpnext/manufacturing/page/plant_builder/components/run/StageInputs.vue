<script setup>
import { computed, inject } from "vue";
import { TextInput } from "frappe-ui";
import { __ } from "../../lib/api";
import { fmt, num } from "../../lib/format";

const props = defineProps({ stage: Object, editable: Boolean });
const run = inject("run");
const tolerance = computed(() => num(run.state.value.plant.doc.formula_tolerance));

const sub = (row) => {
	if (row.is_balance_item) return __("Balance, tops the batch up");
	if (row.is_fixed) return __("Whole batch from the stage before");
	return row.source_warehouse;
};
const canEdit = (row) => props.editable && !row.is_balance_item && !row.is_fixed;
const isOff = (row) => {
	if (row.is_balance_item || row.is_fixed || !row.planned_qty) return false;
	const actual = run.actualOf(props.stage, row);
	return Math.abs(((actual - row.planned_qty) / row.planned_qty) * 100) > tolerance.value + 0.0001;
};

defineExpose({ isOff });
</script>

<template>
	<div class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
		<div
			class="grid h-8 grid-cols-[minmax(0,1fr)_5.25rem_5.5rem] items-center gap-2 px-3 text-xs text-ink-gray-5"
		>
			<span>{{ __("Item") }}</span>
			<span class="text-right">{{ __("Planned") }}</span>
			<span class="text-right">{{ __("Actual") }}</span>
		</div>
		<div
			v-for="row in stage.items"
			:key="row.item_code"
			class="grid h-12 grid-cols-[minmax(0,1fr)_5.25rem_5.5rem] items-center gap-2 px-3"
		>
			<div class="min-w-0">
				<p class="truncate text-sm text-ink-gray-8" :title="row.item_name">{{ row.item_name }}</p>
				<p class="truncate text-xs text-ink-gray-5">{{ sub(row) }}</p>
			</div>
			<span class="truncate whitespace-nowrap text-right text-sm tabular-nums text-ink-gray-6">
				{{ fmt(row.planned_qty) }} {{ row.uom }}
			</span>
			<TextInput
				v-if="canEdit(row)"
				v-model="run.local.actual[stage.idx][row.item_code]"
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
