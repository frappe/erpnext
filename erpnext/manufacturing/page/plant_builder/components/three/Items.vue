<script setup>
import { computed } from "vue";
import Box from "./Box.vue";
import { vLoop } from "../../lib/motion";

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

const COUNT = 7;
const SPEED = 34;
const travel = computed(() => props.len - 16);
const duration = computed(() => (travel.value / SPEED) * 1000);
const at = (position) => Math.min(1, Math.max(0, (position - props.x) / travel.value));

const show = (from, to) => ({ from, to });
const parts = computed(() => {
	const fill = at(props.fillAt);
	const seal = at(props.sealAt);
	return props.kind === "bag"
		? [
				{
					key: "empty",
					...show(0, fill),
					box: { y: props.y - 10, z: props.z, w: 14, d: 20, h: 2, tone: "sack" },
				},
				{
					key: "full",
					...show(fill, 1),
					box: { y: props.y - 10, z: props.z, w: 14, d: 20, h: 8, tone: props.color },
				},
				{
					key: "seal",
					...show(seal, 1),
					box: { y: props.y - 10, z: props.z + 8, w: 14, d: 3, h: 2, tone: "dark" },
				},
		  ]
		: [
				{
					key: "empty",
					...show(0, fill),
					box: { y: props.y - 4, z: props.z, w: 8, d: 8, h: 18, tone: "glass" },
				},
				{
					key: "full",
					...show(fill, 1),
					box: { y: props.y - 4, z: props.z, w: 8, d: 8, h: 18, tone: props.color },
				},
				{
					key: "seal",
					...show(seal, 1),
					box: { x: 1, y: props.y - 3, z: props.z + 18, w: 6, d: 6, h: 4, tone: "dark" },
				},
		  ];
});

const delay = (i) => -(i / COUNT) * duration.value;
const move = (i) => ({
	keyframes: [{ transform: "translateX(0px)" }, { transform: `translateX(${travel.value}px)` }],
	duration: duration.value,
	delay: delay(i),
});
function visible(part, i) {
	const step = (offset, on) => ({ transform: on ? "scale(1)" : "scale(0)", offset });
	const keyframes =
		part.from <= 0
			? [step(0, true), step(part.to, true), step(Math.min(1, part.to + 0.001), false), step(1, false)]
			: [
					step(0, false),
					step(part.from, false),
					step(Math.min(1, part.from + 0.001), true),
					step(1, true),
			  ];
	return { keyframes, duration: duration.value, delay: delay(i) };
}
</script>

<template>
	<template v-if="running">
		<div
			v-for="i in COUNT"
			:key="i"
			v-loop="move(i - 1)"
			class="absolute left-0 top-0"
			:style="{ transformStyle: 'preserve-3d' }"
		>
			<div
				v-for="part in parts"
				:key="part.key"
				v-loop="visible(part, i - 1)"
				class="absolute left-0 top-0"
				:style="{ transformStyle: 'preserve-3d' }"
			>
				<Box v-bind="part.box" :x="x + (part.box.x || 0)" />
			</div>
		</div>
	</template>
</template>
