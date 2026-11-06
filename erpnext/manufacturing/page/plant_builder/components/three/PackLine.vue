<script setup>
import { computed } from "vue";
import Box from "./Box.vue";
import Tank from "./Tank.vue";
import Bobber from "./Bobber.vue";
import Items from "./Items.vue";
import Beacon from "./Beacon.vue";
import PulseRing from "./PulseRing.vue";

const props = defineProps({
	machineModel: String,
	x0: Number,
	yc: Number,
	level: { type: Number, default: 0 },
	color: { type: String, default: "red" },
	mode: { type: String, default: "off" },
	working: Boolean,
	active: Boolean,
	crates: { type: Number, default: 1 },
	packaging: { type: Array, default: () => [] },
});

const bag = computed(() => props.machineModel === "Bagging Line");
const crateList = computed(() =>
	props.packaging.slice(0, 3).map((name, k) => ({ k, x: props.x0 + 20 + k * 100 }))
);
</script>

<template>
	<PulseRing :x="x0 + 175" :y="yc" :w="290" :h="100" :running="mode === 'run'" />
	<Tank :x="x0 + 50" :y="yc" :r="34" :h="110" :level="level" :liquid="color" :active="active" />
	<Box :x="x0 + 90" :y="yc - 12" :w="210" :d="24" :h="30" tone="belt" />
	<Items
		:x="x0 + 93"
		:y="yc"
		:z="30"
		:len="205"
		:fill-at="x0 + 168"
		:seal-at="x0 + 240"
		:kind="bag ? 'bag' : 'bottle'"
		:color="color"
		:running="working"
	/>
	<template v-if="bag">
		<Box :x="x0 + 122" :y="yc - 26" :w="6" :d="6" :h="72" tone="dark" />
		<Box :x="x0 + 122" :y="yc + 20" :w="6" :d="6" :h="72" tone="dark" />
		<Box :x="x0 + 166" :y="yc - 26" :w="6" :d="6" :h="72" tone="dark" />
		<Box :x="x0 + 166" :y="yc + 20" :w="6" :d="6" :h="72" tone="dark" />
		<Tank :x="x0 + 147" :y="yc" :z="72" :r="28" :h="44" :level="working ? 70 : 30" :liquid="color" open />
		<Box :x="x0 + 215" :y="yc - 24" :z="30" :w="30" :d="5" :h="36" tone="steel" />
		<Box :x="x0 + 215" :y="yc + 19" :z="30" :w="30" :d="5" :h="36" tone="steel" />
		<Box :x="x0 + 215" :y="yc - 24" :z="66" :w="30" :d="48" :h="5" tone="steel" />
		<Bobber
			:x="x0 + 220"
			:y="yc - 12"
			:z="54"
			:w="20"
			:d="24"
			:h="8"
			:amp="12"
			:speed="4"
			:running="working"
		/>
	</template>
	<template v-else>
		<Box :x="x0 + 130" :y="yc - 23" :z="30" :w="40" :d="6" :h="46" tone="steel" />
		<Box :x="x0 + 130" :y="yc + 27" :z="30" :w="40" :d="6" :h="46" tone="steel" />
		<Box :x="x0 + 130" :y="yc - 23" :z="76" :w="40" :d="56" :h="6" tone="steel" />
		<Bobber
			:x="x0 + 138"
			:y="yc - 12"
			:z="62"
			:w="24"
			:d="24"
			:h="14"
			:amp="9"
			:speed="4"
			:running="working"
		/>
		<Box :x="x0 + 215" :y="yc - 22" :z="30" :w="28" :d="5" :h="34" tone="steel" />
		<Box :x="x0 + 215" :y="yc + 17" :z="30" :w="28" :d="5" :h="34" tone="steel" />
		<Box :x="x0 + 215" :y="yc - 22" :z="64" :w="28" :d="44" :h="5" tone="steel" />
		<Bobber
			:x="x0 + 221"
			:y="yc - 9"
			:z="56"
			:w="16"
			:d="18"
			:h="8"
			:amp="4"
			:speed="4"
			:phase="1.2"
			:running="working"
		/>
	</template>
	<Box
		v-for="c in crateList"
		:key="c.k"
		:x="c.x"
		:y="40"
		:w="80"
		:d="64"
		:h="6 + 38 * crates"
		tone="crate"
	/>
	<Beacon :x="x0 + 296" :y="yc + 52" :pole="64" :mode="mode" />
</template>
