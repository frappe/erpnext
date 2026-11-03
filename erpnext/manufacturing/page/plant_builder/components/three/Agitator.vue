<script setup>
import { computed } from "vue";
import { vLoop } from "../../lib/motion";

const props = defineProps({
	x: Number,
	y: Number,
	z: Number,
	running: Boolean,
	size: { type: Number, default: 52 },
});

const spin = computed(() =>
	props.running
		? {
				keyframes: [
					{ transform: `translateZ(${props.z}px) rotateZ(0deg)` },
					{ transform: `translateZ(${props.z}px) rotateZ(360deg)` },
				],
				duration: 667,
		  }
		: null
);
</script>

<template>
	<div
		v-loop="spin"
		class="absolute"
		:style="{
			left: `${x}px`,
			top: `${y}px`,
			width: 0,
			height: 0,
			transform: `translateZ(${z}px)`,
			transformStyle: 'preserve-3d',
		}"
	>
		<div
			class="absolute rounded-full bg-surface-gray-7"
			:style="{ left: `${-size / 2}px`, top: '-3px', width: `${size}px`, height: '6px' }"
		/>
		<div
			class="absolute rounded-full bg-surface-gray-7"
			:style="{ left: '-3px', top: `${-size / 2}px`, width: '6px', height: `${size}px` }"
		/>
	</div>
</template>
