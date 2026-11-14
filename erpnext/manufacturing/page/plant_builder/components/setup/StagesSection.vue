<script setup>
import { computed, inject, ref } from "vue";
import { Button, Dropdown } from "frappe-ui";
import SectionHead from "./SectionHead.vue";
import StageCard from "./StageCard.vue";
import { __ } from "../../lib/api";
import { isPackingModel, machineOf } from "../../lib/machines";
import { READ_ONLY, insertStage, machineModelOf } from "../../lib/plant";
import { num } from "../../lib/format";

const props = defineProps({
	doc: Object,
	machines: Object,
	catalog: { type: Array, default: () => [] },
	outputs: { type: Object, default: () => ({}) },
	data: { type: Object, default: () => ({}) },
	focus: { type: Number, default: null },
});
const readOnly = inject(READ_ONLY, ref(false));
const emit = defineEmits(["focus"]);

const models = computed(() => props.doc.stages.map((stage) => machineModelOf(stage, props.machines)));
const hasPacking = computed(() => models.value.some(isPackingModel));
const items = computed(() => props.data.items || {});

function addStage(type) {
	const stage = {
		operation_id: Math.max(0, ...props.doc.stages.map((stage) => num(stage.operation_id))) + 1,
		workstation: "",
		workstation_type: type.name,
		machine_model: type.machine_model,
		operation: "",
		semi_finished_good: "",
		yield_percentage: 100,
		time_in_mins: 30,
	};
	const stages = props.doc.stages;
	const packingAt = models.value.findIndex(isPackingModel);
	const at = isPackingModel(type.machine_model) || packingAt < 0 ? stages.length : packingAt;
	insertStage(props.doc, at, stage);
}

const addOptions = computed(() =>
	props.catalog
		.filter((type) => !isPackingModel(type.machine_model) || !hasPacking.value)
		.map((type) => ({
			label: type.name,
			icon: machineOf(type.machine_model).icon,
			onClick: () => addStage(type),
		}))
);
</script>

<template>
	<section class="space-y-3">
		<SectionHead :title="__('Process Stages')" />
		<StageCard
			v-for="(stage, i) in doc.stages"
			:key="stage.operation_id || i"
			:doc="doc"
			:stage="stage"
			:index="i"
			:machine-model="models[i]"
			:output="outputs[stage.operation_id]"
			:output-uom="items[stage.semi_finished_good]?.stock_uom"
			:data="data"
			:packing-index="models.findIndex(isPackingModel)"
			:focused="focus === i"
			@focus="emit('focus', $event)"
		/>
		<Dropdown v-if="addOptions.length && !readOnly" :options="addOptions">
			<Button icon-left="lucide-plus" :label="__('Add Stage')" />
		</Dropdown>
		<p v-else-if="!readOnly" class="text-p-sm text-ink-gray-5">
			{{ __("Set a Machine Model on a Workstation Type to add stages for it.") }}
		</p>
	</section>
</template>
