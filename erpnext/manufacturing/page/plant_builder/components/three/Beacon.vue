<script setup>
import { computed } from "vue";
import Box from "./Box.vue";
import { clock } from "../../lib/clock";

const props = defineProps({
	x: Number,
	y: Number,
	z: { type: Number, default: 0 },
	pole: { type: Number, default: 70 },
	mode: String,
});

const BLINK = { run: ["go", "godim"], down: ["down", "downdim"] };

const tone = computed(() => {
	if (props.mode === "hold") return "hold";
	if (!BLINK[props.mode]) return "off";
	const [on, dim] = BLINK[props.mode];
	return (clock.value * 2) % 1 < 0.55 ? on : dim;
});
</script>

<template>
	<Box :x="x - 10" :y="y - 10" :z="z" :w="24" :d="24" :h="4" tone="dark" />
	<Box :x="x - 1" :y="y - 1" :z="z + 4" :w="6" :d="6" :h="pole" tone="dark" />
	<Box :x="x - 10" :y="y - 10" :z="z + 4 + pole" :w="24" :d="24" :h="26" :tone="tone" />
	<Box :x="x - 8" :y="y - 8" :z="z + 30 + pole" :w="20" :d="20" :h="4" tone="dark" />
</template>
