<script setup>
import { computed } from "vue";
import { vLoop } from "../../lib/motion";

const props = defineProps({ x: Number, y: Number, r: Number, h: Number, running: Boolean });

const PERIOD = 1667;
const at = (z, opacity, offset) => ({ transform: `translateZ(${z}px) rotateX(-90deg)`, opacity, offset });

const dots = computed(() => {
	if (!props.running || props.h < 12) return [];
	const top = 6 + 0.9 * (props.h - 10);
	return Array.from({ length: 8 }, (_, i) => {
		const s = 3 + (i % 3) * 2;
		const dx = ((i * 37) % (props.r * 1.2)) - props.r * 0.6;
		return {
			i,
			left: props.x + dx - s / 2,
			s,
			rise: {
				keyframes: [at(6, 0.85, 0), at(top, 0.85, 0.9), at(top, 0, 0.91), at(props.h - 4, 0, 1)],
				duration: PERIOD,
				delay: -((i * 0.137) % 1) * PERIOD,
			},
		};
	});
});
</script>

<template>
	<div
		v-for="d in dots"
		:key="d.i"
		v-loop="d.rise"
		class="pointer-events-none absolute rounded-full border border-outline-gray-3 bg-surface-gray-1"
		:style="{
			left: `${d.left}px`,
			top: `${y + r + 1}px`,
			width: `${d.s}px`,
			height: `${d.s}px`,
			opacity: 0,
			transform: 'translateZ(6px) rotateX(-90deg)',
		}"
	/>
</template>
