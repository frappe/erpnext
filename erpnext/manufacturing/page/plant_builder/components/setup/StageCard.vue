<script setup>
import { computed } from "vue";
import { Badge, Button, FormControl, Switch, TextInput, Tooltip } from "frappe-ui";
import DeskControl from "../DeskControl.vue";
import { __ } from "../../lib/api";
import { isPackingModel, machineOf } from "../../lib/machines";
import { moveStage, removeStage, runsWithStageAbove, setRunsWithStageAbove } from "../../lib/plant";

const props = defineProps({
	doc: Object,
	stage: Object,
	index: Number,
	machineModel: String,
	focused: Boolean,
});
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
const canRunInParallel = computed(() => !isPacking.value && props.index > 0);
const parallel = computed({
	get: () => runsWithStageAbove(stages.value, props.index),
	set: (value) => setRunsWithStageAbove(props.doc, props.index, value),
});
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
				{{ stage.stage_name || __(machine.label) }}
			</p>
			<Badge v-if="parallel" :label="__('With Stage {0}', [index])" theme="blue" variant="subtle" />
			<Tooltip :text="__('Move Up')">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-arrow-up"
					:disabled="!canUp"
					@click="move(-1)"
				/>
			</Tooltip>
			<Tooltip :text="__('Move Down')">
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-arrow-down"
					:disabled="!canDown"
					@click="move(1)"
				/>
			</Tooltip>
			<Tooltip :text="__('Remove Stage')">
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
				<FormControl v-model="stage.stage_name" :label="__('Stage Name')" />
				<DeskControl
					v-model="stage.workstation"
					options="Workstation"
					:label="__('Machine')"
					:filters="workstationFilters"
				/>
			</div>
			<div class="grid grid-cols-2 gap-3">
				<DeskControl v-model="stage.operation" options="Operation" :label="__('Operation')" />
				<FormControl v-model="stage.time_in_mins" type="number" :label="__('Minutes')" />
			</div>
			<Switch
				v-if="canRunInParallel"
				v-model="parallel"
				:label="__('Run with the Stage Above')"
				:description="
					__('Both stages run at the same time. The next stage takes the output of both.')
				"
			/>
			<template v-if="!isPacking">
				<DeskControl
					v-model="stage.semi_finished_good"
					options="Item"
					:label="__('Semi-finished Good')"
					:filters="{ is_stock_item: 1 }"
				/>
				<FormControl
					v-model="stage.yield_percentage"
					type="number"
					:label="__('Yield (%)')"
					:description="__('Share of the weight that comes out of this stage')"
				/>
			</template>
			<div v-else class="space-y-2">
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
						variant="ghost"
						size="sm"
						icon="lucide-x"
						:aria-label="__('Remove')"
						@click="removePacking(row)"
					/>
				</div>
				<Button
					size="sm"
					icon-left="lucide-plus"
					:label="__('Add Packing Material')"
					@click="addPacking"
				/>
			</div>
		</div>
	</div>
</template>
