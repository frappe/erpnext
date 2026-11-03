<script setup>
import { computed } from "vue";
import Box from "./Box.vue";
import Tank from "./Tank.vue";
import Agitator from "./Agitator.vue";
import Steam from "./Steam.vue";
import Bubbles from "./Bubbles.vue";
import Fizz from "./Fizz.vue";
import FlowStrip from "./FlowStrip.vue";
import Beacon from "./Beacon.vue";
import PulseRing from "./PulseRing.vue";
import { SHAPES, machineBounds, stageShapes } from "../../lib/machines";
import { num } from "../../lib/format";
import { vLoop } from "../../lib/motion";

const props = defineProps({
	machineModel: String,
	shapes: { type: Array, default: () => [] },
	x: Number,
	y: Number,
	level: { type: Number, default: 0 },
	color: { type: String, default: "red" },
	mode: { type: String, default: "off" },
	working: Boolean,
	active: Boolean,
	rot: Number,
	tilt: Number,
});

const STEAM_TONES = { Blue: "bg-surface-blue-1" };

const design = computed(() => stageShapes({ machine_model: props.machineModel, shapes: props.shapes }));
const bounds = computed(() => machineBounds(design.value));
const half = computed(() => Math.max(-bounds.value.left, bounds.value.right));
const deep = computed(() => Math.max(-bounds.value.back, bounds.value.front));
const ring = computed(() => {
	const w = half.value * 2 + 34;
	return { w, h: bounds.value.round ? w : Math.max(120, deep.value * 2 + 34) };
});
const JITTER = [
	[0.9, 0],
	[-0.5, 0.9],
	[0.4, -0.9],
	[-0.9, -0.4],
	[0.9, 0],
];
const shake = (lift) => ({
	keyframes: JITTER.map(([dx, dy]) => ({ transform: `translate3d(${dx}px, ${dy}px, ${lift}px)` })),
	duration: 180,
});
const heat = computed(() => (props.working ? "red" : "amber"));

function tone(shape) {
	const finish = shape.finish || SHAPES[shape.shape]?.finish || "Steel";
	if (finish === "Product") return props.color;
	if (finish === "Heat") return heat.value;
	return finish.toLowerCase();
}

const flat = (s, at) => ({
	x: at.x - num(s.width) / 2,
	y: at.y - num(s.depth) / 2,
	z: at.z,
	w: num(s.width),
	d: num(s.depth),
});
const round = (s, at) => ({ ...at, r: num(s.radius), h: num(s.height) });
const filled = (s) => (props.level / 100) * num(s.height);

const DRAW = {
	Box: (s, at) => [Box, { ...flat(s, at), h: num(s.height), tone: tone(s) }],
	Tank: (s, at) => [
		Tank,
		{ ...round(s, at), level: s.shows_level ? props.level : 0, liquid: tone(s), active: props.active },
	],
	"Open Tank": (s, at) => [Tank, { ...DRAW.Tank(s, at)[1], open: true }],
	Band: (s, at) => [Tank, { ...round(s, at), level: props.working ? 100 : 0, liquid: tone(s), bare: true }],
	Agitator: (s, at) => [Agitator, { ...at, size: num(s.radius) * 2, running: props.working }],
	Steam: (s, at) => [
		Steam,
		{
			...at,
			rot: props.rot,
			tilt: props.tilt,
			small: !!s.is_small,
			tone: STEAM_TONES[s.finish],
			running: props.working,
		},
	],
	Bubbles: (s, at) => [Bubbles, { ...at, z: at.z + filled(s), running: props.working }],
	Fizz: (s, at) => [
		Fizz,
		{ x: at.x, y: at.y, r: num(s.radius), h: filled(s), running: props.working },
		at.z,
	],
	"Flow Strip": (s, at) => [FlowStrip, { ...flat(s, at), color: tone(s), running: props.working }],
};

const parts = computed(() =>
	design.value
		.filter((s) => DRAW[s.shape])
		.map((s, i) => {
			const at = { x: props.x + num(s.x), y: props.y + num(s.y), z: num(s.z) };
			const [is, attrs, lift = 0] = DRAW[s.shape](s, at);
			return { i, is, attrs, lift, shakes: !!s.shakes };
		})
);
</script>

<template>
	<PulseRing :x="x" :y="y" :w="ring.w" :h="ring.h" :round="bounds.round" :running="mode === 'run'" />
	<div
		v-for="part in parts"
		:key="part.i"
		v-loop="part.shakes && working ? shake(part.lift) : null"
		class="absolute left-0 top-0"
		:style="{ transform: `translateZ(${part.lift}px)`, transformStyle: 'preserve-3d' }"
	>
		<component :is="part.is" v-bind="part.attrs" />
	</div>
	<Beacon :x="x + half + 18" :y="y + Math.max(96, deep + 34)" :pole="70" :mode="mode" />
</template>
