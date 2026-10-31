<script setup>
import { computed } from "vue";
import { clock } from "../../lib/clock";

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

const puffs = computed(() => {
	if (!props.running) return [];
	const k = props.small ? 0.5 : 1;
	return Array.from({ length: 7 }, (_, i) => {
		const p = (clock.value * 0.45 + i / 7) % 1;
		return {
			i,
			z: props.z + 6 + p * 110 * k,
			s: (16 + p * 36) * k,
			o: 0.6 * (1 - p),
			dx: Math.sin((p + i) * 3) * 14 * k,
		};
	});
});
</script>

<template>
	<div
		v-for="p in puffs"
		:key="p.i"
		class="pointer-events-none absolute"
		:style="{
			left: `${x + p.dx}px`,
			top: `${y}px`,
			width: 0,
			height: 0,
			transform: `translateZ(${p.z}px) rotateZ(${-rot}deg) rotateX(${-tilt}deg)`,
			transformStyle: 'preserve-3d',
		}"
	>
		<div
			class="absolute rounded-full"
			:class="tone"
			:style="{
				left: `${-p.s / 2}px`,
				top: `${-p.s / 2}px`,
				width: `${p.s}px`,
				height: `${p.s}px`,
				opacity: p.o,
			}"
		/>
	</div>
</template>
