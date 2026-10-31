<script setup>
import { computed } from "vue";
import { clock } from "../../lib/clock";

const props = defineProps({ x: Number, y: Number, r: Number, h: Number, running: Boolean });

const dots = computed(() => {
	if (!props.running || props.h < 12) return [];
	return Array.from({ length: 12 }, (_, i) => {
		const p = (clock.value * 0.6 + i * 0.137) % 1;
		const s = 3 + (i % 3) * 2;
		const dx = ((i * 37) % (props.r * 1.2)) - props.r * 0.6;
		return { i, left: props.x + dx - s / 2, z: 6 + p * (props.h - 10), s, o: p < 0.9 ? 0.85 : 0 };
	});
});
</script>

<template>
	<div
		v-for="d in dots"
		:key="d.i"
		class="pointer-events-none absolute rounded-full border border-outline-gray-3 bg-surface-gray-1"
		:style="{
			left: `${d.left}px`,
			top: `${y + r + 1}px`,
			width: `${d.s}px`,
			height: `${d.s}px`,
			opacity: d.o,
			transform: `translateZ(${d.z}px) rotateX(-90deg)`,
		}"
	/>
</template>
