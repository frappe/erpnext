<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";

import TaskRow from "./TaskRow.vue";

// A list's rows, drawn a batch at a time: the first batch at once, the next ones as the list
// scrolls near its end, so a project with thousands of tasks still groups and searches quickly.
const props = defineProps({
	tasks: { type: Array, required: true },
	columns: { type: Array, required: true },
	indent: { type: Number, default: 0 },
	// changes when the rows are another set (grouping, sort or search), not when a task is
	// edited, so an edit doesn't scroll the list back
	view_key: { type: String, default: "" },
	first: { type: Number, default: 60 },
});

const BATCH = 200;
const shown = ref(props.first);
watch(
	() => props.view_key,
	() => (shown.value = props.first)
);
const visible = computed(() => props.tasks.slice(0, shown.value));
const more = computed(() => shown.value < props.tasks.length);

// a marker after the last row; once it comes near the screen, the next batch is drawn
const marker = ref(null);
let observer = null;
watch(marker, (element) => {
	observer?.disconnect();
	if (!element) return;
	observer = new IntersectionObserver(([entry]) => entry.isIntersecting && (shown.value += BATCH), {
		rootMargin: "800px 0px",
	});
	observer.observe(element);
});
onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
	<TaskRow v-for="task in visible" :key="task.name" :task="task" :columns="columns" :indent="indent" />
	<div v-if="more" ref="marker" class="h-px" aria-hidden="true" />
</template>
