<script setup>
import { computed } from "vue";
import FloorList from "./views/FloorList.vue";
import FloorView from "./views/FloorView.vue";
import PlantRun from "./views/PlantRun.vue";
import MachineDesigner from "./views/MachineDesigner.vue";
import ProcessDesign from "./views/ProcessDesign.vue";

const props = defineProps({
	route: { type: Array, default: () => [] },
	query: { type: Object, default: () => ({}) },
	design: { type: Object, default: null },
	readOnly: Boolean,
});
const emit = defineEmits(["title", "actions", "change", "update"]);

const part = (index) => (props.route[index] ? decodeURIComponent(props.route[index]) : null);
const machine = computed(() => (props.route[2] === "design" ? part(1) : null));
const workOrder = computed(() => (props.route[0] === "run" && props.route.length === 2 ? part(1) : null));
const floor = computed(() => (props.route.length === 1 ? part(0) : null));
const chrome = {
	onTitle: (title) => emit("title", title),
	onActions: (actions) => emit("actions", actions),
};

function selectNumber(event) {
	if (event.target.matches('input[type="number"]')) event.target.select();
}
</script>

<template>
	<div
		class="flex h-full flex-col bg-surface-base text-ink-gray-9 [&_input[type=number]::-webkit-inner-spin-button]:appearance-none [&_input[type=number]::-webkit-outer-spin-button]:appearance-none [&_input[type=number]]:[appearance:textfield]"
		@focusin="selectNumber"
	>
		<ProcessDesign
			v-if="design"
			:design="design"
			:read-only="readOnly"
			@change="emit('change', $event)"
			@update="emit('update', $event)"
		/>
		<MachineDesigner v-else-if="machine" :key="machine" :name="machine" v-bind="chrome" />
		<PlantRun v-else-if="workOrder" :key="workOrder" :work-order="workOrder" v-bind="chrome" />
		<FloorView v-else-if="floor" :key="floor" :name="floor" v-bind="chrome" />
		<FloorList v-else v-bind="chrome" />
	</div>
</template>
