<script setup>
import { computed } from "vue";
import { INK } from "../../lib/machines";
import { vLoop } from "../../lib/motion";

const props = defineProps({
	x: Number,
	y: Number,
	w: Number,
	d: Number,
	z: Number,
	color: { type: String, default: "red" },
	vertical: Boolean,
	sign: { type: Number, default: 1 },
	running: Boolean,
});

const stripes = computed(() => ({
	inset: props.vertical ? "-16px 0" : "0 -16px",
	backgroundImage: `repeating-linear-gradient(${
		props.vertical ? 180 : 90
	}deg, currentColor 0 8px, transparent 8px 16px)`,
}));
const flow = computed(() => {
	const axis = props.vertical ? "Y" : "X";
	return {
		keyframes: [
			{ transform: `translate${axis}(0px)` },
			{ transform: `translate${axis}(${16 * props.sign}px)` },
		],
		duration: 444,
	};
});
</script>

<template>
	<div
		v-if="running"
		class="pointer-events-none absolute overflow-hidden"
		:class="INK[color] ?? INK.gray"
		:style="{
			left: `${x}px`,
			top: `${y}px`,
			width: `${w}px`,
			height: `${d}px`,
			transform: `translateZ(${z}px)`,
		}"
	>
		<div v-loop="flow" class="absolute" :style="stripes" />
	</div>
</template>
