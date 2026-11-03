<script setup>
import { computed } from "vue";
import { vLoop } from "../../lib/motion";

const props = defineProps({ x: Number, y: Number, z: Number, running: Boolean });

const SPOTS = [
	[-24, -12],
	[16, -28],
	[28, 14],
	[-10, 26],
	[2, 0],
	[34, -8],
];
const PERIOD = 909;
const grow = (z) => {
	const at = (scale, opacity, offset) => ({
		transform: `translateZ(${z + 1}px) scale(${scale})`,
		opacity,
		offset,
	});
	return {
		keyframes: [at(0.21, 0.9, 0), at(0.86, 0.9, 0.85), at(0.86, 0, 0.86), at(1, 0, 1)],
		duration: PERIOD,
	};
};

const bubbles = computed(() =>
	props.running
		? SPOTS.map(([dx, dy], i) => ({
				i,
				left: props.x + dx - 7,
				top: props.y + dy - 7,
				grow: { ...grow(props.z), delay: -((i * 0.37) % 1) * PERIOD },
		  }))
		: []
);
</script>

<template>
	<div
		v-for="b in bubbles"
		:key="b.i"
		v-loop="b.grow"
		class="pointer-events-none absolute rounded-full border border-outline-gray-3 bg-surface-gray-1"
		:style="{
			left: `${b.left}px`,
			top: `${b.top}px`,
			width: '14px',
			height: '14px',
			opacity: 0,
			transform: `translateZ(${z + 1}px) scale(0.21)`,
		}"
	/>
</template>
