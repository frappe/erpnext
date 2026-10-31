<script setup>
import { computed } from "vue";
import { clock } from "../../lib/clock";

const props = defineProps({ x: Number, y: Number, w: Number, h: Number, round: Boolean, running: Boolean });

const rings = computed(() => {
	if (!props.running) return [];
	return [0, 0.5].map((offset, i) => {
		const p = (clock.value * 0.7 + offset) % 1;
		return { i, scale: 1 + p * 0.22, opacity: 0.9 * (1 - p) };
	});
});
</script>

<template>
	<div
		v-for="r in rings"
		:key="r.i"
		class="pointer-events-none absolute border-2 border-outline-green-4"
		:class="round ? 'rounded-full' : 'rounded-6'"
		:style="{
			left: `${x - w / 2}px`,
			top: `${y - h / 2}px`,
			width: `${w}px`,
			height: `${h}px`,
			opacity: r.opacity,
			transform: `translateZ(1px) scale(${r.scale})`,
		}"
	/>
</template>
