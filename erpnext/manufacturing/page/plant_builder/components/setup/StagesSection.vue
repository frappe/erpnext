<script setup>
import { computed } from "vue";
import { Button, Dropdown } from "frappe-ui";
import SectionHead from "./SectionHead.vue";
import StageCard from "./StageCard.vue";
import { __ } from "../../lib/api";
import { MACHINES, machineKey, machineOf } from "../../lib/machines";

const props = defineProps({
	doc: Object,
	machines: Object,
	catalog: { type: Array, default: () => [] },
	focus: { type: Number, default: null },
});
const emit = defineEmits(["focus"]);

const stageMachine = (stage) =>
	machineKey(props.machines[stage.workstation]?.machine_model || stage.machine_model);
const isPackingStage = (stage) => MACHINES[stageMachine(stage)].kind === "pack";
const isPackingType = (type) => machineOf(type.machine_model).kind === "pack";
const hasPacking = computed(() => props.doc.stages.some(isPackingStage));

function addStage(type) {
	const machine = machineOf(type.machine_model);
	const stage = {
		stage_name: machine.stage,
		workstation: "",
		workstation_type: type.name,
		machine_model: type.machine_model,
		operation: "",
		semi_finished_good: "",
		yield_percentage: 100,
		time_in_mins: 30,
	};
	const stages = props.doc.stages;
	const packingAt = stages.findIndex(isPackingStage);
	if (machine.kind === "pack" || packingAt < 0) stages.push(stage);
	else stages.splice(packingAt, 0, stage);
}

const addOptions = computed(() =>
	props.catalog
		.filter((type) => !isPackingType(type) || !hasPacking.value)
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
					'Each stage is one machine. It takes the batch from the stage before and makes a semi-finished good. The last stage packs the finished good.'
				)
			"
		/>
		<StageCard
			v-for="(stage, i) in doc.stages"
			:key="stage.name || i"
			:doc="doc"
			:stage="stage"
			:index="i"
			:machine="stageMachine(stage)"
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
