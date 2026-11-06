<script setup>
import { computed } from "vue";
import Box from "./Box.vue";
import { vLoop } from "../../lib/motion";

const props = defineProps({
	x: Number,
	y: Number,
	z: Number,
	w: Number,
	d: Number,
	h: Number,
	amp: { type: Number, default: 10 },
	speed: { type: Number, default: 3 },
	phase: { type: Number, default: 0 },
	running: Boolean,
	tone: { type: String, default: "dark" },
});

const bob = computed(() => {
	if (!props.running) return null;
	const duration = (Math.PI / props.speed) * 1000;
	const at = (dz, easing) => ({ transform: `translateZ(${props.z - dz}px)`, easing });
	return {
		keyframes: [at(0, "ease-out"), at(props.amp, "ease-in"), at(0)],
		duration,
		delay: -((props.phase % Math.PI) / Math.PI) * duration,
	};
});
</script>

<template>
	<Box v-loop="bob" :x="x" :y="y" :z="z" :w="w" :d="d" :h="h" :tone="tone" />
</template>
