<script setup>
import { computed } from "vue";
import { INK } from "../../lib/machines";
import { clock } from "../../lib/clock";

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

const style = computed(() => {
	const shift = ((clock.value * 36) % 16) * props.sign;
	return {
		left: `${props.x}px`,
		top: `${props.y}px`,
		width: `${props.w}px`,
		height: `${props.d}px`,
		transform: `translateZ(${props.z}px)`,
		backgroundImage: `repeating-linear-gradient(${
			props.vertical ? 180 : 90
		}deg, currentColor 0 8px, transparent 8px 16px)`,
		backgroundPosition: props.vertical ? `0 ${shift}px` : `${shift}px 0`,
	};
});
</script>

<template>
	<div v-if="running" class="pointer-events-none absolute" :class="INK[color] ?? INK.gray" :style="style" />
</template>
