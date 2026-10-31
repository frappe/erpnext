<script setup>
import { computed } from "vue";
import { clock } from "../../lib/clock";

const props = defineProps({ x: Number, y: Number, z: Number, running: Boolean });

const SPOTS = [
	[-24, -12],
	[16, -28],
	[28, 14],
	[-10, 26],
	[2, 0],
	[-34, 14],
	[34, -8],
	[-6, -36],
];

const bubbles = computed(() => {
	if (!props.running) return [];
	return SPOTS.map(([dx, dy], i) => {
		const p = (clock.value * 1.1 + i * 0.37) % 1;
		const s = 3 + p * 11;
		return { i, left: props.x + dx - s / 2, top: props.y + dy - s / 2, s, o: p < 0.85 ? 0.9 : 0 };
	});
});
</script>

<template>
	<div
		v-for="b in bubbles"
		:key="b.i"
		class="pointer-events-none absolute rounded-full border border-outline-gray-3 bg-surface-gray-1"
		:style="{
			left: `${b.left}px`,
			top: `${b.top}px`,
			width: `${b.s}px`,
			height: `${b.s}px`,
			opacity: b.o,
			transform: `translateZ(${z + 1}px)`,
		}"
	/>
</template>
