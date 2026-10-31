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
import { MACHINES } from "../../lib/machines";
import { clock } from "../../lib/clock";

const props = defineProps({
	type: String,
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

const SHAKERS = ["mixer", "mill", "dryer"];
const ROUND = ["mixer", "kettle", "reactor", "fermenter"];

const half = computed(() => MACHINES[props.type]?.half ?? 50);
const jitter = computed(() => {
	if (!props.working || !SHAKERS.includes(props.type)) return "none";
	const t = clock.value;
	return `translate3d(${Math.sin(t * 71) * 0.9}px, ${Math.cos(t * 53) * 0.9}px, 0)`;
});
const heatTone = computed(() => (props.working && (clock.value * 1.4) % 1 < 0.5 ? "red" : "amber"));
const plates = Array.from({ length: 7 }, (_, i) => i);
</script>

<template>
	<PulseRing
		:x="x"
		:y="y"
		:w="half * 2 + 34"
		:h="ROUND.includes(type) ? half * 2 + 34 : 120"
		:round="ROUND.includes(type)"
		:running="mode === 'run'"
	/>
	<div class="absolute left-0 top-0" :style="{ transform: jitter, transformStyle: 'preserve-3d' }">
		<template v-if="type === 'mixer'">
			<Tank :x="x" :y="y" :r="56" :h="140" :level="level" :liquid="color" :active="active" />
			<Box :x="x - 14" :y="y - 14" :z="140" :w="28" :d="28" :h="22" tone="dark" />
			<Agitator :x="x" :y="y" :z="163" :running="working" />
		</template>
		<template v-else-if="type === 'kettle'">
			<Tank :x="x" :y="y" :r="62" :h="110" :level="level" :liquid="color" open :active="active" />
			<Bubbles :x="x" :y="y" :z="level * 1.1" :running="working" />
			<Steam :x="x" :y="y" :z="110" :rot="rot" :tilt="tilt" :running="working" />
		</template>
		<template v-else-if="type === 'reactor'">
			<Tank :x="x" :y="y" :r="50" :h="170" :level="level" :liquid="color" :active="active" />
			<Tank :x="x" :y="y" :z="34" :r="54" :h="16" :level="working ? 100 : 0" :liquid="heatTone" bare />
			<Tank :x="x" :y="y" :z="104" :r="54" :h="16" :level="working ? 100 : 0" :liquid="heatTone" bare />
			<Box :x="x - 8" :y="y - 8" :z="170" :w="16" :d="16" :h="16" tone="dark" />
			<Steam :x="x" :y="y" :z="186" :rot="rot" :tilt="tilt" small :running="working" />
		</template>
		<template v-else-if="type === 'fermenter'">
			<Tank :x="x" :y="y" :r="46" :h="180" :level="level" :liquid="color" :active="active" />
			<Box :x="x - 6" :y="y - 6" :z="180" :w="12" :d="12" :h="12" tone="dark" />
			<Fizz :x="x" :y="y" :r="46" :h="level * 1.8" :running="working" />
		</template>
		<template v-else-if="type === 'mill'">
			<Box :x="x - 48" :y="y - 36" :w="96" :d="72" :h="54" tone="steel" />
			<Box :x="x + 48" :y="y - 16" :z="8" :w="22" :d="32" :h="30" tone="dark" />
			<Tank
				:x="x - 12"
				:y="y"
				:z="54"
				:r="24"
				:h="36"
				:level="level"
				:liquid="color"
				open
				:active="active"
			/>
			<Agitator :x="x + 59" :y="y" :z="39" :size="30" :running="working" />
			<Steam :x="x - 12" :y="y" :z="90" :rot="rot" :tilt="tilt" small :running="working" />
		</template>
		<template v-else-if="type === 'dryer'">
			<Box :x="x - 80" :y="y - 32" :z="10" :w="160" :d="64" :h="58" tone="steel" />
			<Box :x="x - 70" :y="y - 28" :w="10" :d="56" :h="10" tone="dark" />
			<Box :x="x + 60" :y="y - 28" :w="10" :d="56" :h="10" tone="dark" />
			<Box :x="x - 100" :y="y - 18" :z="14" :w="20" :d="36" :h="36" tone="dark" />
			<FlowStrip :x="x - 76" :y="y - 28" :w="152" :d="56" :z="69" color="amber" :running="working" />
			<Steam :x="x + 64" :y="y" :z="68" :rot="rot" :tilt="tilt" :running="working" />
		</template>
		<template v-else-if="type === 'generic'">
			<Box :x="x - 44" :y="y - 36" :w="88" :d="72" :h="80" tone="steel" />
			<Box :x="x - 30" :y="y - 22" :z="80" :w="60" :d="44" :h="12" tone="dark" />
			<FlowStrip :x="x - 30" :y="y - 4" :w="60" :d="8" :z="92.5" :color="color" :running="working" />
		</template>
		<template v-else-if="type === 'cooler'">
			<Box :x="x - 42" :y="y - 32" :w="84" :d="64" :h="8" tone="dark" />
			<Box
				v-for="i in plates"
				:key="i"
				:x="x - 38 + i * 11"
				:y="y - 28"
				:z="8"
				:w="7"
				:d="56"
				:h="82"
				tone="plate"
			/>
			<Box :x="x - 42" :y="y - 4" :z="90" :w="84" :d="8" :h="8" tone="steel" />
			<FlowStrip :x="x - 42" :y="y - 4" :w="84" :d="8" :z="98.5" color="blue" :running="working" />
			<Steam
				:x="x"
				:y="y"
				:z="92"
				:rot="rot"
				:tilt="tilt"
				small
				tone="bg-surface-blue-1"
				:running="working"
			/>
		</template>
	</div>
	<Beacon :x="x + half + 18" :y="y + 96" :pole="70" :mode="mode" />
</template>
