<script setup>
import { computed } from "vue";
import Box from "./Box.vue";
import { vLoop } from "../../lib/motion";

const props = defineProps({
	x: Number,
	y: Number,
	z: { type: Number, default: 0 },
	pole: { type: Number, default: 70 },
	mode: String,
});

const BLINK = { run: ["go", "godim"], down: ["down", "downdim"] };
const BLINK_ON = {
	keyframes: [
		{ transform: "scale(1)", offset: 0 },
		{ transform: "scale(1)", offset: 0.55 },
		{ transform: "scale(0)", offset: 0.551 },
		{ transform: "scale(0)", offset: 1 },
	],
	duration: 500,
};

const blink = computed(() => BLINK[props.mode]);
const tone = computed(() => {
	if (props.mode === "hold") return "hold";
	return blink.value ? blink.value[1] : "off";
});
</script>

<template>
	<Box :x="x - 10" :y="y - 10" :z="z" :w="24" :d="24" :h="4" tone="dark" />
	<Box :x="x - 1" :y="y - 1" :z="z + 4" :w="6" :d="6" :h="pole" tone="dark" />
	<Box :x="x - 10" :y="y - 10" :z="z + 4 + pole" :w="24" :d="24" :h="26" :tone="tone" />
	<div
		v-if="blink"
		v-loop="BLINK_ON"
		class="absolute left-0 top-0"
		:style="{ transformStyle: 'preserve-3d' }"
	>
		<Box :x="x - 10.5" :y="y - 10.5" :z="z + 3.5 + pole" :w="25" :d="25" :h="27" :tone="blink[0]" />
	</div>
	<Box :x="x - 8" :y="y - 8" :z="z + 30 + pole" :w="20" :d="20" :h="4" tone="dark" />
</template>
