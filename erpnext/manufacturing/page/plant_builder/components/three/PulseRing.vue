<script setup>
import { vLoop } from "../../lib/motion";

defineProps({ x: Number, y: Number, w: Number, h: Number, round: Boolean, running: Boolean });

const PERIOD = 1430;
const pulse = (offset) => ({
	keyframes: [
		{ transform: "translateZ(1px) scale(1)", opacity: 0.9 },
		{ transform: "translateZ(1px) scale(1.22)", opacity: 0 },
	],
	duration: PERIOD,
	delay: -offset * PERIOD,
});
</script>

<template>
	<template v-if="running">
		<div
			v-for="offset in [0, 0.5]"
			:key="offset"
			v-loop="pulse(offset)"
			class="pointer-events-none absolute border-2 border-outline-green-4"
			:class="round ? 'rounded-full' : 'rounded-6'"
			:style="{
				left: `${x - w / 2}px`,
				top: `${y - h / 2}px`,
				width: `${w}px`,
				height: `${h}px`,
				opacity: 0,
				transform: 'translateZ(1px)',
			}"
		/>
	</template>
</template>
