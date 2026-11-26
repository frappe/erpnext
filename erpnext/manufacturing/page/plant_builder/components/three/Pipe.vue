<script setup>
import { computed } from "vue";
import FlowStrip from "./FlowStrip.vue";

const props = defineProps({
	x1: Number,
	y1: Number,
	x2: Number,
	y2: Number,
	flowing: Boolean,
	color: { type: String, default: "red" },
});

const T = 8;
const LIFT = 4;
const across = computed(() => props.y1 === props.y2);
const rect = computed(() => ({
	x: Math.min(props.x1, props.x2) - T / 2,
	y: Math.min(props.y1, props.y2) - T / 2,
	w: Math.abs(props.x2 - props.x1) + T,
	d: Math.abs(props.y2 - props.y1) + T,
}));
const sign = computed(
	() => (across.value ? Math.sign(props.x2 - props.x1) : Math.sign(props.y2 - props.y1)) || 1
);
</script>

<template>
	<div
		class="absolute border border-outline-gray-4 bg-surface-gray-2"
		:style="{
			left: `${rect.x}px`,
			top: `${rect.y}px`,
			width: `${rect.w}px`,
			height: `${rect.d}px`,
			transform: `translateZ(${LIFT}px)`,
			transformStyle: 'preserve-3d',
		}"
	>
		<FlowStrip
			:x="0"
			:y="0"
			:w="rect.w - 2"
			:d="rect.d - 2"
			:z="0.5"
			:color="color"
			:vertical="!across"
			:sign="sign"
			:running="flowing"
		/>
	</div>
</template>
