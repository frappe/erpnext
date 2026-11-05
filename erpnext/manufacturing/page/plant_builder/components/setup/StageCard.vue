<script setup>
import { computed, inject, ref } from "vue";
import { Button, FormControl, TextInput, Tooltip } from "frappe-ui";
import DeskControl from "../DeskControl.vue";
import StageMaterials from "./StageMaterials.vue";
import { __ } from "../../lib/api";
import { fmt } from "../../lib/format";
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
const runsWithOptions = computed(() => [
	{ label: __("None"), value: "" },
	...stageOptions.value.map((option) => ({ label: option.label, value: String(option.stageNo) })),
]);
const runsWith = computed(() => {
	const other = groupOf(stages.value, props.index).find((stage) => stage !== props.stage);
	return other ? String(stages.value.indexOf(other) + 1) : "";
});
const setRunsWithStage = (value) => setRunsWith(props.doc, props.index, value ? Number(value) - 1 : null);

const packing = computed(() => props.doc.packing_materials);
const addPacking = () => packing.value.push({ item_code: "", qty_per_unit: 1 });
const removePacking = (row) => packing.value.splice(packing.value.indexOf(row), 1);
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
					<DeskControl
						:model-value="runsWith"
						fieldtype="Select"
						:options="runsWithOptions"
						:label="__('Runs With')"
						@update:model-value="setRunsWithStage"
					/>
					<FormControl
						v-model="stage.time_in_mins"
						type="number"
						variant="outline"
						:label="__('Minutes')"
					/>
				</div>
				<StageMaterials :doc="doc" :data="data" :stage-no="index + 1" :stage-options="stageOptions" />
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
				<p class="text-sm text-ink-gray-6">
					{{ __("Packing materials, per unit of the finished good") }}
				</p>
				<div
					v-for="(row, i) in packing"
					:key="row.name || i"
					class="grid grid-cols-[minmax(0,1fr)_5rem_1.75rem] items-center gap-2"
				>
					<DeskControl v-model="row.item_code" options="Item" :filters="{ is_stock_item: 1 }" />
					<TextInput
						v-model="row.qty_per_unit"
						type="number"
						size="sm"
						class="[&_input]:bg-surface-base [&_input]:text-right"
					/>
					<Button
						v-if="!readOnly"
						variant="ghost"
						size="sm"
						icon="lucide-x"
						:aria-label="__('Remove')"
						@click="removePacking(row)"
					/>
				</div>
				<Button
					v-if="!readOnly"
					size="sm"
					icon-left="lucide-plus"
					:label="__('Add Packing Material')"
					@click="addPacking"
				/>
			</div>
		</div>
	</div>
</template>
