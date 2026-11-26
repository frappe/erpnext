<script setup>
import { computed } from "vue";
import { vLoop } from "../../lib/motion";

const props = defineProps({
	x: Number,
	y: Number,
	z: Number,
	rot: Number,
	tilt: Number,
	running: Boolean,
	small: Boolean,
	tone: { type: String, default: "bg-surface-gray-3" },
});

const PERIOD = 2222;
const PUFFS = 5;
const k = computed(() => (props.small ? 0.5 : 1));
const puffs = computed(() =>
	props.running
		? Array.from({ length: PUFFS }, (_, i) => ({
				i,
				s: 16 * k.value,
				rise: {
					keyframes: [
						{ transform: "translate(0px, 0px) scale(1)", opacity: 0.6 },
						{
							transform: `translate(${Math.sin(i * 3) * 14 * k.value}px, ${
								-96 * k.value
							}px) scale(3.25)`,
							opacity: 0,
						},
					],
					duration: PERIOD,
					delay: -(i / PUFFS) * PERIOD,
				},
		  }))
		: []
);
</script>

<template>
	<div
		v-if="running"
		class="pointer-events-none absolute"
		:style="{
			left: `${x}px`,
			top: `${y}px`,
			width: 0,
			height: 0,
			transform: `translateZ(${z + 6}px) rotateZ(${-rot}deg) rotateX(${-tilt}deg)`,
			transformStyle: 'preserve-3d',
		}"
	>
		<div
			v-for="p in puffs"
			:key="p.i"
			v-loop="p.rise"
			class="absolute rounded-full"
			:class="tone"
			:style="{
				left: `${-p.s / 2}px`,
				top: `${-p.s / 2}px`,
				width: `${p.s}px`,
				height: `${p.s}px`,
				opacity: 0,
			}"
		/>
	</div>
</template>
