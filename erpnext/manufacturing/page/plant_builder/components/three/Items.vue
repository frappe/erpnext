<script setup>
import { computed } from "vue";
import Box from "./Box.vue";
import { clock } from "../../lib/clock";

const props = defineProps({
	x: Number,
	y: Number,
	z: Number,
	len: Number,
	fillAt: Number,
	sealAt: Number,
	running: Boolean,
	kind: { type: String, default: "bottle" },
	color: { type: String, default: "red" },
});

const items = computed(() => {
	if (!props.running) return [];
	const gap = props.len / 7;
	return Array.from({ length: 7 }, (_, i) => {
		const bx = props.x + ((clock.value * 34 + i * gap) % (props.len - 16));
		return { i, x: bx, full: bx > props.fillAt, sealed: bx > props.sealAt };
	});
});
</script>

<template>
	<template v-for="b in items" :key="b.i">
		<template v-if="kind === 'bag'">
			<Box
				:x="b.x"
				:y="y - 10"
				:z="z"
				:w="14"
				:d="20"
				:h="b.full ? 8 : 2"
				:tone="b.full ? color : 'sack'"
			/>
			<Box v-if="b.sealed" :x="b.x" :y="y - 10" :z="z + 8" :w="14" :d="3" :h="2" tone="dark" />
		</template>
		<template v-else>
			<Box :x="b.x" :y="y - 4" :z="z" :w="8" :d="8" :h="18" :tone="b.full ? color : 'glass'" />
			<Box v-if="b.sealed" :x="b.x + 1" :y="y - 3" :z="z + 18" :w="6" :d="6" :h="4" tone="dark" />
		</template>
	</template>
</template>
