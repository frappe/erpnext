<script setup>
import { computed } from "vue";
import { Button, Dropdown } from "frappe-ui";
import SectionHead from "./SectionHead.vue";
import StageCard from "./StageCard.vue";
import { __ } from "../../lib/api";
import { isPackingModel, machineOf } from "../../lib/machines";
import { insertStage, machineModelOf } from "../../lib/plant";

const props = defineProps({
	doc: Object,
	machines: Object,
	catalog: { type: Array, default: () => [] },
	focus: { type: Number, default: null },
});
const emit = defineEmits(["focus"]);

const models = computed(() => props.doc.stages.map((stage) => machineModelOf(stage, props.machines)));
const hasPacking = computed(() => models.value.some(isPackingModel));

function addStage(type) {
	const machine = machineOf(type.machine_model);
	const stage = {
		stage_name: __(machine.stage),
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
		<SectionHead
			:title="__('Process Stages')"
			:description="
				__(
					'Each stage is one machine that makes a semi-finished good. It takes the output of the stage before it, or of every stage that runs with it. The last stage packs the finished good.'
				)
			"
		/>
		<StageCard
			v-for="(stage, i) in doc.stages"
			:key="stage.name || i"
			:doc="doc"
			:stage="stage"
			:index="i"
			:machine-model="models[i]"
			:focused="focus === i"
			@focus="emit('focus', $event)"
		/>
		<Dropdown v-if="addOptions.length" :options="addOptions">
			<Button icon-left="lucide-plus" :label="__('Add Stage')" />
		</Dropdown>
		<p v-else class="text-p-sm text-ink-gray-5">
			{{ __("Set a Machine Model on a Workstation Type to add stages for it.") }}
		</p>
	</section>
</template>
