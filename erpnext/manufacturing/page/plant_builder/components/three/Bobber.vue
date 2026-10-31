<script setup>
import { computed } from "vue";
import Box from "./Box.vue";
import { clock } from "../../lib/clock";

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

const dz = computed(() =>
	props.running ? props.amp * Math.abs(Math.sin(clock.value * props.speed + props.phase)) : 0
);
</script>

<template>
	<Box :x="x" :y="y" :z="z - dz" :w="w" :d="d" :h="h" :tone="tone" />
</template>
