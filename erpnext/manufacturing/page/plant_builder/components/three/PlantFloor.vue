<script setup>
import { computed } from "vue";
import Box from "./Box.vue";
import Tank from "./Tank.vue";
import Pipe from "./Pipe.vue";
import MachineModel from "./MachineModel.vue";
import PackLine from "./PackLine.vue";

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
	const list = [{ key: "store", label: "Raw material store", ...L.store.zone, active: v.storeActive }];
	L.stations.forEach((st) =>
		list.push({
			key: st.stage.id,
			label: `${st.i + 1}  ${st.stage.name || "Stage"}`,
			...st.zone,
			active: v.active[st.i],
		})
	);
	if (L.fg) list.push({ key: "fg", label: "Finished goods", ...L.fg, active: v.fgActive });
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
	return Array.from({ length: Math.round(24 * props.view.cartons) }, (_, i) => {
		const j = i % 12;
		return {
			i,
			x: fg.x + 89 + (j % 4) * 36,
			y: fg.y + 34 + Math.floor(j / 4) * 38,
			z: 10 + Math.floor(i / 12) * 27,
		};
	});
});

const lvl = (key) => props.view.level[key] ?? 0;
</script>

<template>
	<div
		v-for="z in zones"
		:key="z.key"
		class="pointer-events-none absolute rounded-5"
		:class="
			z.active
				? 'border-2 border-outline-gray-7 bg-surface-gray-2'
				: 'border border-dashed border-outline-gray-4'
		"
		:style="{ left: `${z.x}px`, top: `${z.y}px`, width: `${z.w}px`, height: `${z.h}px` }"
	>
		<span
			class="absolute bottom-2 left-3 max-w-[90%] origin-bottom-left truncate whitespace-nowrap text-lg-semibold"
			:class="z.active ? 'text-ink-gray-8' : 'text-ink-gray-5'"
			:style="{ transform: `scale(${Math.min(k, 1.8)})` }"
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
			:type="st.stage.machine"
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
			:type="st.stage.machine"
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
			:z="c.z"
			:w="34"
			:d="36"
			:h="26"
			tone="carton"
		/>
	</template>
</template>
