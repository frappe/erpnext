<script setup>
import { computed } from "vue";
import PlantList from "./views/PlantList.vue";
import PlantSetup from "./views/PlantSetup.vue";
import PlantRun from "./views/PlantRun.vue";

const props = defineProps({
	route: { type: Array, default: () => [] },
	query: { type: Object, default: () => ({}) },
});
const emit = defineEmits(["title", "actions"]);

const plant = computed(() => (props.route[0] ? decodeURIComponent(props.route[0]) : null));
const workOrder = computed(() => (props.route[1] ? decodeURIComponent(props.route[1]) : null));
const chrome = {
	onTitle: (title) => emit("title", title),
	onActions: (actions) => emit("actions", actions),
};
</script>

<template>
	<div class="flex h-full flex-col bg-surface-base text-ink-gray-9">
		<PlantRun
			v-if="plant && workOrder"
			:key="workOrder"
			:plant="plant"
			:work-order="workOrder"
			v-bind="chrome"
		/>
		<PlantSetup v-else-if="plant" :key="plant" :name="plant" v-bind="chrome" />
		<PlantList v-else v-bind="chrome" />
	</div>
</template>
