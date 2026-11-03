<script setup>
import { computed, ref } from "vue";
import { useElementSize } from "@vueuse/core";
import { Button, Progress, TabButtons, Tooltip } from "frappe-ui";
import PlantFloor from "./PlantFloor.vue";
import { buildLayout } from "../../lib/layout";
import { buildTags, useOrbitCamera } from "../../lib/scene";
import { useClock } from "../../lib/clock";
import { __ } from "../../lib/api";
import { clamp } from "../../lib/format";

const props = defineProps({
	plant: Object,
	view: Object,
	live: { type: Object, default: () => ({}) },
	chip: { type: Object, default: null },
	paused: Boolean,
});
const emit = defineEmits(["resume"]);

const PERSPECTIVE = 2200;

const layout = computed(() => buildLayout(props.plant));
const tags = computed(() => buildTags(props.plant, layout.value, props.view, props.live));

const stage = ref(null);
const { viewName, rot, tilt, zoom, dragging, animateTo, setView, zoomBy, onWheel, onDown } = useOrbitCamera();

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
					{ label: __('3D'), value: '3d' },
					{ label: __('Top'), value: 'top' },
					{ label: __('Front'), value: 'front' },
				]"
				@update:model-value="setView"
			/>
			<div
				class="flex items-center gap-0.5 rounded-4 border border-outline-gray-2 bg-surface-base p-0.5"
			>
				<Tooltip :text="__('Rotate left')"
					><Button variant="ghost" icon="lucide-rotate-ccw" @click="animateTo(rot - 45, tilt)"
				/></Tooltip>
				<Tooltip :text="__('Rotate right')"
					><Button variant="ghost" icon="lucide-rotate-cw" @click="animateTo(rot + 45, tilt)"
				/></Tooltip>
				<Tooltip :text="__('Zoom out')"
					><Button variant="ghost" icon="lucide-zoom-out" @click="zoomBy(-0.2)"
				/></Tooltip>
				<Tooltip :text="__('Zoom in')"
					><Button variant="ghost" icon="lucide-zoom-in" @click="zoomBy(0.2)"
				/></Tooltip>
				<Tooltip :text="__('Fit plant')"
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
					:label="__('Resume')"
					@click="emit('resume')"
				/>
			</div>
			<Progress v-if="chip.progress !== null" :value="chip.progress" size="sm" />
		</div>

		<p class="pointer-events-none absolute bottom-3 left-3 text-xs text-ink-gray-5">
			{{ __("Drag to rotate · Scroll to zoom") }}
		</p>
	</div>
</template>
