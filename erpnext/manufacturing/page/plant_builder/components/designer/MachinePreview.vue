<script setup>
import { computed, ref } from "vue";
import { useElementSize, useEventListener } from "@vueuse/core";
import { Button, TabButtons, Tooltip } from "frappe-ui";
import MachineModel from "../three/MachineModel.vue";
import { shapeExtent } from "../../lib/machines";
import { useClock } from "../../lib/clock";

const props = defineProps({
	type: String,
	shapes: Array,
	selected: { type: Number, default: null },
	running: Boolean,
});

const FLOOR = 480;
const CENTRE = FLOOR / 2;
const VIEWS = { "3d": [-24, 56], top: [0, 0], front: [0, 72] };

const stage = ref(null);
const viewName = ref("3d");
const rot = ref(-24);
const tilt = ref(56);
const zoom = ref(1);
const orbit = { on: false, x: 0, y: 0 };
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

const { width, height } = useElementSize(stage);
useClock(stage);

const scale = computed(() => clamp(Math.min(width.value, height.value) / 760, 0.4, 2) * zoom.value);
const floorStyle = computed(() => ({
	left: `${width.value / 2}px`,
	top: `${height.value / 2 + 40}px`,
	width: `${FLOOR}px`,
	height: `${FLOOR}px`,
	transform: `translate(-50%, -50%) scale(${scale.value}) rotateX(${tilt.value}deg) rotateZ(${rot.value}deg)`,
	transformStyle: "preserve-3d",
}));
const grid = {
	backgroundImage:
		"linear-gradient(currentColor 1px, transparent 1px), linear-gradient(90deg, currentColor 1px, transparent 1px)",
	backgroundSize: "20px 20px",
};

const outline = computed(() => {
	const shape = props.shapes[props.selected];
	if (!shape) return [];
	const e = shapeExtent(shape);
	const box = {
		left: `${CENTRE + e.x - e.halfX - 4}px`,
		top: `${CENTRE + e.y - e.halfY - 4}px`,
		width: `${e.halfX * 2 + 8}px`,
		height: `${e.halfY * 2 + 8}px`,
	};
	return [...new Set([e.z, e.top])].map((z) => ({
		z,
		round: e.round,
		style: { ...box, transform: `translateZ(${z + 1}px)` },
	}));
});

function setView(name) {
	viewName.value = name;
	[rot.value, tilt.value] = VIEWS[name];
}

function onDown(e) {
	if (e.button === 0) Object.assign(orbit, { on: true, x: e.clientX, y: e.clientY });
}

useEventListener(window, "pointermove", (e) => {
	if (!orbit.on) return;
	rot.value += (e.clientX - orbit.x) * 0.35;
	tilt.value = clamp(tilt.value - (e.clientY - orbit.y) * 0.3, 0, 80);
	Object.assign(orbit, { x: e.clientX, y: e.clientY });
});
useEventListener(window, "pointerup", () => (orbit.on = false));
</script>

<template>
	<div class="absolute inset-0 overflow-hidden">
		<div
			ref="stage"
			class="absolute inset-0 cursor-grab select-none"
			:style="{ perspective: '2200px', touchAction: 'none' }"
			@pointerdown="onDown"
			@wheel.prevent="zoom = clamp(zoom - $event.deltaY * 0.0015, 0.5, 3)"
		>
			<div class="absolute rounded-5 border border-outline-gray-3 bg-surface-base" :style="floorStyle">
				<div class="pointer-events-none absolute inset-0 rounded-5 text-ink-gray-2" :style="grid" />
				<div class="absolute inset-y-0 w-px bg-surface-gray-4" :style="{ left: `${CENTRE}px` }" />
				<div class="absolute inset-x-0 h-px bg-surface-gray-4" :style="{ top: `${CENTRE}px` }" />
				<MachineModel
					:type="type"
					:shapes="shapes"
					:x="CENTRE"
					:y="CENTRE"
					:level="60"
					:mode="running ? 'run' : 'off'"
					:working="running"
					:rot="rot"
					:tilt="tilt"
				/>
				<div
					v-for="line in outline"
					:key="line.z"
					class="pointer-events-none absolute border-2 border-dashed border-outline-blue-4"
					:class="line.round ? 'rounded-full' : 'rounded-2'"
					:style="line.style"
				/>
			</div>
		</div>

		<div class="absolute left-3 top-3">
			<slot name="overlay" />
		</div>

		<div class="absolute right-3 top-3 flex items-center gap-2">
			<TabButtons
				:model-value="viewName"
				:options="[
					{ label: '3D', value: '3d' },
					{ label: 'Top', value: 'top' },
					{ label: 'Front', value: 'front' },
				]"
				@update:model-value="setView"
			/>
			<div
				class="flex items-center gap-0.5 rounded-4 border border-outline-gray-2 bg-surface-base p-0.5"
			>
				<Tooltip text="Zoom out"
					><Button variant="ghost" icon="lucide-zoom-out" @click="zoom = clamp(zoom - 0.2, 0.5, 3)"
				/></Tooltip>
				<Tooltip text="Zoom in"
					><Button variant="ghost" icon="lucide-zoom-in" @click="zoom = clamp(zoom + 0.2, 0.5, 3)"
				/></Tooltip>
			</div>
		</div>

		<p class="pointer-events-none absolute bottom-3 left-3 text-xs text-ink-gray-5">
			Drag to rotate · Scroll to zoom
		</p>
	</div>
</template>
