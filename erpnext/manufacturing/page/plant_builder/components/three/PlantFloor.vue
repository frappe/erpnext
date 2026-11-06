<script setup>
import { computed } from "vue";
import Box from "./Box.vue";
import Tank from "./Tank.vue";
import Pipe from "./Pipe.vue";
import MachineModel from "./MachineModel.vue";
import PackLine from "./PackLine.vue";
import { __ } from "../../lib/api";

const emit = defineEmits(["hover"]);
const props = defineProps({
	plant: Object,
	layout: Object,
	view: Object,
	rot: Number,
	tilt: Number,
	k: Number,
});

const SACK_LIGHT = ["gray", "cream", "blue"];

const zones = computed(() => {
	const L = props.layout;
	const v = props.view;
	const list = L.store.zone
		? [
				{
					key: "store",
					tag: null,
					label: __("Raw material store"),
					...L.store.zone,
					active: v.storeActive,
				},
		  ]
		: [];
	L.stations.forEach((st) =>
		list.push({
			key: st.stage.id,
			tag: `s${st.i}`,
			label: props.plant.floor ? st.stage.name : `${st.i + 1}  ${st.stage.name || __("Stage")}`,
			...st.zone,
			active: v.active[st.i],
			down: v.mode[st.i] === "down",
		})
	);
	if (L.fg) list.push({ key: "fg", tag: "fg", label: __("Finished goods"), ...L.fg, active: v.fgActive });
	return list;
});

function sacksFor(it) {
	const lvl = props.view.level[`m:${it.m.id}`] ?? 0;
	const count = Math.max(0, Math.min(6, Math.round((6 * lvl) / 80)));
	const tone = SACK_LIGHT.includes(it.m.color) ? "sack" : it.m.color;
	return Array.from({ length: count }, (_, k) => ({
		k,
		x: it.x - 56 + (k % 3) * 38,
		y: it.y - 36 + Math.floor(k / 3) * 38,
		tone,
	}));
}

const cartons = computed(() => {
	const fg = props.layout.fg;
	if (!fg) return [];
	const count = Math.round(24 * props.view.cartons);
	return Array.from({ length: Math.min(count, 12) }, (_, i) => ({
		i,
		x: fg.x + 89 + (i % 4) * 36,
		y: fg.y + 34 + Math.floor(i / 4) * 38,
		h: i < count - 12 ? 53 : 26,
	}));
});
const lvl = (key) => props.view.level[key] ?? 0;
const LABEL_CHAR = 10;
function zoneLabel(zone) {
	const room = zone.w - 24;
	const readable = Math.min(props.k, 1.8);
	const scale = Math.max(readable * 0.6, Math.min(readable, room / (zone.label.length * LABEL_CHAR)));
	return { transform: `scale(${scale})`, maxWidth: `${room / scale}px` };
}

function zoneClass(zone) {
	if (zone.down) return "border-2 border-outline-red-4 bg-surface-red-1";
	if (zone.active) return "border-2 border-outline-gray-7 bg-surface-gray-2";
	return "border border-dashed border-outline-gray-4";
}
</script>

<template>
	<div
		v-for="z in zones"
		:key="z.key"
		class="pointer-events-auto absolute rounded-5"
		:class="zoneClass(z)"
		:style="{ left: `${z.x}px`, top: `${z.y}px`, width: `${z.w}px`, height: `${z.h}px` }"
		@pointerenter="emit('hover', z.tag)"
		@pointerleave="emit('hover', null)"
	>
		<span
			class="absolute bottom-2 left-3 origin-bottom-left truncate whitespace-nowrap text-lg-semibold"
			:class="z.down ? 'text-ink-red-5' : z.active ? 'text-ink-gray-8' : 'text-ink-gray-5'"
			:style="zoneLabel(z)"
		>
			{{ z.label }}
		</span>
	</div>

	<Pipe
		v-for="(p, i) in layout.pipes"
		:key="`p${i}`"
		v-bind="p"
		:flowing="p.flow.some((stage) => view.flow[stage])"
	/>

	<div
		v-for="it in layout.store.items"
		:key="`hit${it.m.id}`"
		class="pointer-events-auto absolute"
		:style="{ left: `${it.x - 65}px`, top: `${it.y - 60}px`, width: '130px', height: '120px' }"
		@pointerenter="emit('hover', `m:${it.m.id}`)"
		@pointerleave="emit('hover', null)"
	/>
	<template v-for="it in layout.store.items" :key="it.m.id">
		<template v-if="it.shape === 'sacks'">
			<Box :x="it.x - 60" :y="it.y - 40" :w="120" :d="80" :h="10" tone="wood" />
			<Box
				v-for="s in sacksFor(it)"
				:key="s.k"
				:x="s.x"
				:y="s.y"
				:z="10"
				:w="36"
				:d="34"
				:h="18"
				:tone="s.tone"
			/>
		</template>
		<Tank
			v-else
			:x="it.x"
			:y="it.y"
			:r="it.r"
			:h="it.h"
			:level="lvl(`m:${it.m.id}`)"
			:liquid="it.m.color"
		/>
	</template>

	<template v-for="st in layout.stations" :key="st.stage.id">
		<PackLine
			v-if="st.pack"
			:machine-model="st.stage.machine_model"
			:x0="st.zone.x"
			:yc="st.y"
			:level="lvl(`s${st.i}`)"
			:color="plant.product.color"
			:mode="view.mode[st.i]"
			:working="view.working[st.i]"
			:active="view.active[st.i]"
			:crates="view.crates"
			:packaging="st.stage.packaging"
		/>
		<MachineModel
			v-else
			:machine-model="st.stage.machine_model"
			:shapes="st.stage.shapes"
			:x="st.x"
			:y="st.y"
			:level="lvl(`s${st.i}`)"
			:color="plant.product.color"
			:mode="view.mode[st.i]"
			:working="view.working[st.i]"
			:active="view.active[st.i]"
			:rot="rot"
			:tilt="tilt"
		/>
	</template>

	<template v-if="layout.fg">
		<Box :x="layout.fg.x + 85" :y="layout.fg.y + 30" :w="150" :d="120" :h="10" tone="wood" />
		<Box
			v-for="c in cartons"
			:key="`c${c.i}`"
			:x="c.x"
			:y="c.y"
			:z="10"
			:w="34"
			:d="36"
			:h="c.h"
			tone="carton"
		/>
	</template>
</template>
