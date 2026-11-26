<script setup>
import { computed, inject, ref } from "vue";
import { Button, FormControl, Select, Tooltip } from "frappe-ui";
import DeskControl from "../DeskControl.vue";
import StageMaterials from "./StageMaterials.vue";
import { __ } from "../../lib/api";
import { fmt, num } from "../../lib/format";
import { isPackingModel, machineOf } from "../../lib/machines";
import { READ_ONLY, groupOf, moveStage, removeStage, setRunsWith } from "../../lib/plant";

const props = defineProps({
	doc: Object,
	stage: Object,
	index: Number,
	machineModel: String,
	output: Number,
	outputUom: String,
	data: { type: Object, default: () => ({}) },
	packingIndex: { type: Number, default: -1 },
	focused: Boolean,
});
const readOnly = inject(READ_ONLY, ref(false));
const emit = defineEmits(["focus"]);

const machine = computed(() => machineOf(props.machineModel));
const isPacking = computed(() => isPackingModel(props.machineModel));
const stages = computed(() => props.doc.stages);
const processCount = computed(() => stages.value.filter((s) => s !== props.stage).length);
const canUp = computed(() => !isPacking.value && props.index > 0);
const canDown = computed(() => !isPacking.value && props.index < stages.value.length - 2);
const canRemove = computed(() => isPacking.value || processCount.value > 0);
const workstationFilters = computed(() =>
	props.stage.workstation_type
		? { workstation_type: props.stage.workstation_type, disabled: 0 }
		: { disabled: 0 }
);

const move = (offset) => moveStage(props.doc, props.index, props.index + offset);
const remove = () => removeStage(props.doc, props.index);
const stageLabel = (stage, i) => {
	const machine = machineOf(stage.machine_model);
	return `${i + 1}. ${stage.operation || __(machine.stage || machine.label)}`;
};
const stageOptions = computed(() =>
	stages.value
		.map((stage, i) => ({ label: stageLabel(stage, i), stageNo: i + 1 }))
		.filter((_, i) => i !== props.index && i !== props.packingIndex)
);
const moveOptions = computed(() =>
	stages.value
		.map((stage, i) => ({ label: stageLabel(stage, i), stageNo: i + 1 }))
		.filter((_, i) => i !== props.index)
);
const runsWith = computed(() => {
	const other = groupOf(stages.value, props.index).find((stage) => stage !== props.stage);
	return other ? String(stages.value.indexOf(other) + 1) : null;
});
const runsWithOptions = computed(() => [
	...stageOptions.value.map((option) => ({ label: option.label, value: String(option.stageNo) })),
	...(runsWith.value ? [{ label: __("No other stage"), value: "" }] : []),
]);
const finishedGood = computed(() => props.data.item || {});
const setRunsWithStage = (value) => setRunsWith(props.doc, props.index, value ? Number(value) - 1 : null);
</script>

<template>
	<div
		class="rounded-5 border bg-surface-base"
		:class="focused ? 'border-outline-gray-5' : 'border-outline-gray-2'"
		@mouseenter="emit('focus', index)"
		@mouseleave="emit('focus', null)"
	>
		<div class="flex h-12 items-center gap-2 border-b border-outline-gray-1 px-3">
			<span
				class="flex size-6 shrink-0 items-center justify-center rounded-full border border-outline-gray-3 text-xs tabular-nums text-ink-gray-6"
			>
				{{ index + 1 }}
			</span>
			<span class="size-4 shrink-0 text-ink-gray-6" :class="machine.icon" aria-hidden="true" />
			<p class="min-w-0 flex-1 truncate text-base font-medium text-ink-gray-8">
				{{ stage.operation || __(machine.stage || machine.label) }}
			</p>
			<Tooltip v-if="!readOnly" :text="__('Move Up')">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-arrow-up"
					:disabled="!canUp"
					@click="move(-1)"
				/>
			</Tooltip>
			<Tooltip v-if="!readOnly" :text="__('Move Down')">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-arrow-down"
					:disabled="!canDown"
					@click="move(1)"
				/>
			</Tooltip>
			<Tooltip v-if="!readOnly" :text="__('Remove Stage')">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-trash-2"
					:disabled="!canRemove"
					@click="remove"
				/>
			</Tooltip>
		</div>
		<div class="space-y-3 p-3">
			<div class="grid grid-cols-2 gap-3">
				<DeskControl v-model="stage.operation" options="Operation" :label="__('Operation')" />
				<DeskControl
					v-model="stage.workstation"
					options="Workstation"
					:label="__('Machine')"
					:filters="workstationFilters"
				/>
			</div>
			<template v-if="!isPacking">
				<div class="grid grid-cols-2 gap-3">
					<Select
						:model-value="runsWith"
						:options="runsWithOptions"
						variant="outline"
						:label="__('Runs With')"
						:placeholder="__('No other stage')"
						:disabled="readOnly || !stageOptions.length"
						@update:model-value="setRunsWithStage"
					/>
					<FormControl
						v-model="stage.time_in_mins"
						type="number"
						variant="outline"
						:label="__('Minutes')"
					/>
				</div>
				<StageMaterials
					:doc="doc"
					:data="data"
					:stage-no="index + 1"
					:packing-no="packingIndex + 1"
					:stage-options="moveOptions"
				/>
				<div class="grid grid-cols-2 gap-3">
					<DeskControl
						v-model="stage.semi_finished_good"
						options="Item"
						:label="__('Semi-finished Good')"
						:filters="{ is_stock_item: 1 }"
						:description="
							output ? __('Makes {0} {1} for each batch', [fmt(output), outputUom || '']) : ''
						"
					/>
					<FormControl
						v-model="stage.yield_percentage"
						type="number"
						variant="outline"
						:label="__('Yield (%)')"
						:description="__('Share of the weight that comes out')"
					/>
				</div>
			</template>
			<div v-else class="space-y-2">
				<FormControl
					v-model="stage.time_in_mins"
					type="number"
					variant="outline"
					:label="__('Minutes')"
				/>
				<StageMaterials
					:doc="doc"
					:data="data"
					:stage-no="index + 1"
					:packing-no="packingIndex + 1"
					:stage-options="moveOptions"
				/>
			</div>
		</div>
		<div
			v-if="isPacking && doc.production_item"
			class="flex h-12 items-center gap-2 border-t border-outline-gray-1 px-3"
		>
			<span class="lucide-package-check size-4 shrink-0 text-ink-gray-6" aria-hidden="true" />
			<div class="min-w-0 flex-1">
				<p class="text-xs text-ink-gray-5">{{ __("Finished Good") }}</p>
				<p class="truncate text-sm font-medium text-ink-gray-8">
					{{ finishedGood.item_name || doc.production_item }}
				</p>
			</div>
			<p class="shrink-0 text-sm font-medium tabular-nums text-ink-gray-8">
				{{ fmt(num(doc.batch_size)) }} {{ finishedGood.stock_uom || "" }}
			</p>
		</div>
	</div>
</template>
