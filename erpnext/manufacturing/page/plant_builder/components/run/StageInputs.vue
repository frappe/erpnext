<script setup>
import { computed, inject, ref } from "vue";
import { Button, TextInput, Tooltip } from "frappe-ui";
import SerialBatchPicker from "./SerialBatchPicker.vue";
import { __ } from "../../lib/api";
import { fmt } from "../../lib/format";

const props = defineProps({ stage: Object, editable: Boolean });
const run = inject("run");

const key = (row) => row.name || row.item_code;
const canPick = (row) => props.editable && !row.is_input && (row.has_serial_no || row.has_batch_no);
const hasPicks = computed(() => props.stage.items.some(canPick));
const columns = computed(() =>
	hasPicks.value
		? "grid-cols-[minmax(0,1fr)_5.25rem_6rem_1.75rem]"
		: "grid-cols-[minmax(0,1fr)_5.25rem_6rem]"
);
const picking = ref(null);
const pickLabel = (row) => (row.has_serial_no ? __("Pick Serial Nos") : __("Pick Batches"));
const sub = (row) => {
	const pick = run.pickOf(props.stage, row);
	if (pick) return pick.label;
	if (row.is_balance_item) return __("Balance, tops the batch up");
	if (!row.is_input) return row.source_warehouse;
	return props.editable ? __("Waiting in {0}", [row.source_stage]) : __("From {0}", [row.source_stage]);
};
const canEdit = (row) => props.editable && !row.is_balance_item;
const isOff = (row) => run.isOff(props.stage, row);
function setActual(row, value) {
	if (value === run.local.actual[props.stage.idx][row.name]) return;
	if (row.is_input) run.setPass(props.stage, row, value);
	else run.setMaterial(props.stage, row, value);
}
</script>

<template>
	<div class="divide-y divide-outline-gray-1 rounded-4 border border-outline-gray-2">
		<div class="grid h-8 items-center gap-2 px-3 text-xs text-ink-gray-5" :class="columns">
			<span>{{ __("Item") }}</span>
			<span class="text-right">{{ __("Planned") }}</span>
			<span class="text-right">{{ editable ? __("Actual") : __("Used") }}</span>
			<span v-if="hasPicks" />
		</div>
		<div
			v-for="row in stage.items"
			:key="key(row)"
			class="grid h-12 items-center gap-2 px-3"
			:class="columns"
		>
			<div class="min-w-0">
				<p class="truncate text-sm text-ink-gray-8" :title="row.item_name">{{ row.item_name }}</p>
				<p class="truncate text-xs text-ink-gray-5">{{ sub(row) }}</p>
			</div>
			<span class="truncate whitespace-nowrap text-right text-sm tabular-nums text-ink-gray-6">
				{{ fmt(run.plannedOf(stage, row)) }} {{ row.uom }}
			</span>
			<TextInput
				v-if="canEdit(row)"
				:model-value="run.local.actual[stage.idx][row.name]"
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
				{{ fmt(run.usedOf(stage, row)) }}
			</span>
			<template v-if="hasPicks">
				<Tooltip v-if="canPick(row)" :text="pickLabel(row)">
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-list-checks"
						:aria-label="pickLabel(row)"
						:class="run.pickOf(stage, row) ? 'text-ink-blue-5' : ''"
						@click="picking = row"
					/>
				</Tooltip>
				<span v-else />
			</template>
		</div>
		<SerialBatchPicker
			v-if="picking"
			:open="!!picking"
			:stage="stage"
			:row="picking"
			@update:open="!$event && (picking = null)"
		/>
	</div>
</template>
