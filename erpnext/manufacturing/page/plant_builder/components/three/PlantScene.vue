<script setup>
import { computed, ref } from "vue";
import { useElementSize, useEventListener } from "@vueuse/core";
import { Button, Progress, TabButtons, Tooltip } from "frappe-ui";
import PlantFloor from "./PlantFloor.vue";
import { buildLayout } from "../../lib/layout";
import { buildTags } from "../../lib/scene";
import { useClock } from "../../lib/clock";

const props = defineProps({
	plant: Object,
	view: Object,
	live: { type: Object, default: () => ({}) },
	chip: { type: Object, default: null },
	paused: Boolean,
});
const emit = defineEmits(["resume"]);

const PERSPECTIVE = 2200;
const PRESETS = { "3d": [-24, 56], top: [0, 0], front: [0, 72] };

const layout = computed(() => buildLayout(props.plant));
const tags = computed(() => buildTags(props.plant, layout.value, props.view, props.live));

const viewName = ref("3d");
const rot = ref(-24);
const tilt = ref(56);
const zoom = ref(1);
const dragging = ref(false);
const stage = ref(null);
const orbit = { on: false, x: 0, y: 0, moved: 0 };
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

const { width, height } = useElementSize(stage);
useClock(stage);
const fit = computed(() => {
	if (!width.value) return 0.5;
	return clamp(
		Math.min((width.value - 40) / layout.value.W, (height.value - 120) / layout.value.H),
		0.15,
		1.6
	);
});
const scale = computed(() => fit.value * zoom.value * (1 - tilt.value / 300));
const center = computed(() => ({ x: width.value / 2, y: height.value / 2 + 50 }));

function animateTo(toRot, toTilt) {
	const from = [rot.value, tilt.value];
	const start = performance.now();
	const step = (now) => {
		const p = Math.min(1, (now - start) / 350);
		const e = 1 - (1 - p) ** 3;
		rot.value = from[0] + (toRot - from[0]) * e;
		tilt.value = from[1] + (toTilt - from[1]) * e;
		if (p < 1) requestAnimationFrame(step);
	};
	requestAnimationFrame(step);
}

function setView(v) {
	viewName.value = v;
	animateTo(...PRESETS[v]);
}

function onDown(e) {
	if (e.button !== 0) return;
	Object.assign(orbit, { on: true, x: e.clientX, y: e.clientY, moved: 0 });
}

useEventListener(window, "pointermove", (e) => {
	if (!orbit.on) return;
	const dx = e.clientX - orbit.x;
	const dy = e.clientY - orbit.y;
	orbit.moved += Math.abs(dx) + Math.abs(dy);
	dragging.value = orbit.moved > 4;
	rot.value += dx * 0.35;
	tilt.value = clamp(tilt.value - dy * 0.3, 0, 80);
	Object.assign(orbit, { x: e.clientX, y: e.clientY });
});

useEventListener(window, "pointerup", () => {
	orbit.on = false;
	dragging.value = false;
});

function onWheel(e) {
	zoom.value = clamp(zoom.value - e.deltaY * 0.0015, 0.5, 3);
}

function project(t) {
	const r = (rot.value * Math.PI) / 180;
	const a = (tilt.value * Math.PI) / 180;
	const x0 = t.x - layout.value.W / 2;
	const y0 = t.y - layout.value.H / 2;
	const x1 = x0 * Math.cos(r) - y0 * Math.sin(r);
	const y1 = x0 * Math.sin(r) + y0 * Math.cos(r);
	const y2 = y1 * Math.cos(a) - t.z * Math.sin(a);
	const z2 = y1 * Math.sin(a) + t.z * Math.cos(a);
	const f = PERSPECTIVE / (PERSPECTIVE - z2);
	return {
		left: `${center.value.x + scale.value * x1 * f}px`,
		top: `${center.value.y + scale.value * y2 * f}px`,
	};
}

const placedTags = computed(() => (width.value ? tags.value.map((t) => ({ ...t, style: project(t) })) : []));

const floorStyle = computed(() => ({
	left: `${center.value.x}px`,
	top: `${center.value.y}px`,
	width: `${layout.value.W}px`,
	height: `${layout.value.H}px`,
	transform: `translate(-50%, -50%) scale(${scale.value}) rotateX(${tilt.value}deg) rotateZ(${rot.value}deg)`,
	transformStyle: "preserve-3d",
}));

const grid = {
	backgroundImage:
		"linear-gradient(currentColor 1px, transparent 1px), linear-gradient(90deg, currentColor 1px, transparent 1px)",
	backgroundSize: "40px 40px",
};
</script>

<template>
	<div class="absolute inset-0 overflow-hidden">
		<div
			ref="stage"
			class="absolute inset-0 select-none"
			:class="dragging ? 'cursor-grabbing' : 'cursor-grab'"
			:style="{
				perspective: `${PERSPECTIVE}px`,
				perspectiveOrigin: `${center.x}px ${center.y}px`,
				touchAction: 'none',
			}"
			@pointerdown="onDown"
			@wheel.prevent="onWheel"
		>
			<div class="absolute rounded-5 border border-outline-gray-3 bg-surface-base" :style="floorStyle">
				<div class="pointer-events-none absolute inset-0 rounded-5 text-ink-gray-2" :style="grid" />
				<PlantFloor
					:plant="plant"
					:layout="layout"
					:view="view"
					:rot="rot"
					:tilt="tilt"
					:k="1 / scale"
				/>
			</div>
		</div>

		<div
			v-for="t in placedTags"
			:key="t.id"
			class="pointer-events-none absolute flex h-6 max-w-[15rem] -translate-x-1/2 -translate-y-full items-center gap-1.5 rounded-4 border bg-surface-base px-2 shadow-sm"
			:class="t.active ? 'border-outline-gray-7' : 'border-outline-gray-2'"
			:style="t.style"
		>
			<span
				class="max-w-[8rem] shrink-0 truncate whitespace-nowrap text-xs font-medium text-ink-gray-8"
				>{{ t.title }}</span
			>
			<span class="min-w-0 truncate text-xs tabular-nums text-ink-gray-5">{{ t.sub }}</span>
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
				<Tooltip text="Rotate left"
					><Button variant="ghost" icon="lucide-rotate-ccw" @click="animateTo(rot - 45, tilt)"
				/></Tooltip>
				<Tooltip text="Rotate right"
					><Button variant="ghost" icon="lucide-rotate-cw" @click="animateTo(rot + 45, tilt)"
				/></Tooltip>
				<Tooltip text="Zoom out"
					><Button variant="ghost" icon="lucide-zoom-out" @click="zoom = clamp(zoom - 0.2, 0.5, 3)"
				/></Tooltip>
				<Tooltip text="Zoom in"
					><Button variant="ghost" icon="lucide-zoom-in" @click="zoom = clamp(zoom + 0.2, 0.5, 3)"
				/></Tooltip>
				<Tooltip text="Fit plant"
					><Button
						variant="ghost"
						icon="lucide-scan"
						@click="
							zoom = 1;
							setView('3d');
						"
				/></Tooltip>
			</div>
		</div>

		<div
			v-if="chip"
			class="absolute bottom-3 flex w-96 -translate-x-1/2 flex-col gap-2 rounded-4 border bg-surface-base px-3 py-2 shadow-sm"
			:class="paused ? 'border-outline-amber-3' : 'pointer-events-none border-outline-gray-2'"
			:style="{ left: `${center.x}px` }"
		>
			<div class="flex h-7 items-center gap-2 text-sm">
				<span v-if="paused" class="lucide-circle-pause size-4 text-ink-amber-5" aria-hidden="true" />
				<span
					v-else
					class="lucide-loader-circle size-4 animate-spin text-ink-gray-5"
					aria-hidden="true"
				/>
				<span class="min-w-0 flex-1 truncate text-ink-gray-8">{{ chip.label }}</span>
				<span v-if="chip.progress !== null" class="w-10 text-right tabular-nums text-ink-gray-5"
					>{{ Math.round(chip.progress) }}%</span
				>
				<Button
					v-if="paused"
					size="sm"
					icon-left="lucide-play"
					label="Resume"
					@click="emit('resume')"
				/>
			</div>
			<Progress v-if="chip.progress !== null" :value="chip.progress" size="sm" />
		</div>

		<p class="pointer-events-none absolute bottom-3 left-3 text-xs text-ink-gray-5">
			Drag to rotate · Scroll to zoom
		</p>
	</div>
</template>
