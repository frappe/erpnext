<script setup>
import { computed, ref } from "vue";
import { useElementSize } from "@vueuse/core";
import { Button, Progress, TabButtons, Tooltip } from "frappe-ui";
import PlantFloor from "./PlantFloor.vue";
import PanButtons from "./PanButtons.vue";
import { buildFloorLayout, buildLayout } from "../../lib/layout";
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

const layout = computed(() => (props.plant.floor ? buildFloorLayout : buildLayout)(props.plant));
const tags = computed(() => buildTags(props.plant, layout.value, props.view, props.live));

const stage = ref(null);
const hovered = ref(null);
const {
	viewName,
	rot,
	tilt,
	zoom,
	pan,
	dragging,
	animateTo,
	setView,
	fit: fitView,
	zoomBy,
	panBy,
	onWheel,
	onDown,
} = useOrbitCamera();

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
const center = computed(() => ({
	x: width.value / 2 + pan.value.x,
	y: height.value / 2 + 50 + pan.value.y,
}));

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
	return { x: center.value.x + scale.value * x1 * f, y: center.value.y + scale.value * y2 * f };
}

const tagRank = (t) =>
	t.id === hovered.value ? -1 : t.active ? 0 : t.id.startsWith("s") ? 1 : t.id === "fg" ? 2 : 3;
const tagWidth = (t) =>
	Math.min(256, 26 + 7.5 * Math.max((t.title || "").length, String(t.sub || "").length));

function clearOf(kept, t) {
	const half = tagWidth(t) / 2 + 4;
	const box = { left: t.at.x - half, right: t.at.x + half, top: t.at.y - 56, bottom: t.at.y + 2 };
	if (
		kept.some((k) => box.left < k.right && box.right > k.left && box.top < k.bottom && box.bottom > k.top)
	)
		return false;
	kept.push(box);
	return true;
}

const placedTags = computed(() => {
	if (!width.value) return [];
	const kept = [];
	return tags.value
		.map((t) => ({ ...t, at: project(t) }))
		.filter((t) => t.active || t.id === hovered.value)
		.sort((a, b) => tagRank(a) - tagRank(b))
		.filter((t) => clearOf(kept, t))
		.map((t) => ({ ...t, style: { left: `${t.at.x}px`, top: `${t.at.y}px` } }));
});

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
			@contextmenu.prevent
			@wheel.prevent="onWheel"
		>
			<div
				class="pointer-events-none absolute rounded-5 border border-outline-gray-3 bg-surface-base"
				:style="floorStyle"
			>
				<div class="pointer-events-none absolute inset-0 rounded-5 text-ink-gray-2" :style="grid" />
				<PlantFloor
					:plant="plant"
					:layout="layout"
					:view="view"
					:rot="rot"
					:tilt="tilt"
					:k="1 / scale"
					@hover="hovered = dragging ? null : $event"
				/>
			</div>
		</div>

		<div
			v-for="t in placedTags"
			:key="t.id"
			class="pointer-events-none absolute max-w-[16rem] -translate-x-1/2 -translate-y-full rounded-6 border bg-surface-base px-3 py-1.5 shadow-md"
			:class="t.active ? 'border-outline-gray-7' : 'border-outline-gray-2'"
			:style="t.style"
		>
			<p class="truncate whitespace-nowrap text-sm font-medium text-ink-gray-8">{{ t.title }}</p>
			<p v-if="t.sub" class="truncate whitespace-nowrap text-sm tabular-nums text-ink-gray-6">
				{{ t.sub }}
			</p>
		</div>

		<div
			class="pointer-events-none absolute inset-x-3 top-3 flex flex-wrap-reverse items-end justify-between gap-2"
		>
			<div v-if="$slots.overlay" class="pointer-events-auto">
				<slot name="overlay" />
			</div>
			<div class="pointer-events-auto ml-auto flex max-w-full flex-wrap items-center justify-end gap-2">
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
					<slot name="tools" />
					<Tooltip :text="__('Rotate left')"
						><Button
							variant="ghost"
							:aria-label="__('Rotate left')"
							icon="lucide-rotate-ccw"
							@click="animateTo(rot - 45, tilt)"
					/></Tooltip>
					<Tooltip :text="__('Rotate right')"
						><Button
							variant="ghost"
							:aria-label="__('Rotate right')"
							icon="lucide-rotate-cw"
							@click="animateTo(rot + 45, tilt)"
					/></Tooltip>
					<Tooltip :text="__('Zoom out')"
						><Button
							variant="ghost"
							:aria-label="__('Zoom out')"
							icon="lucide-zoom-out"
							@click="zoomBy(-0.2)"
					/></Tooltip>
					<Tooltip :text="__('Zoom in')"
						><Button
							variant="ghost"
							:aria-label="__('Zoom in')"
							icon="lucide-zoom-in"
							@click="zoomBy(0.2)"
					/></Tooltip>
					<Tooltip :text="__('Fit plant')"
						><Button
							variant="ghost"
							:aria-label="__('Fit plant')"
							icon="lucide-scan"
							@click="fitView"
					/></Tooltip>
				</div>
				<PanButtons :pan-by="panBy" />
			</div>
		</div>

		<div
			v-if="chip"
			class="absolute bottom-3 flex w-96 -translate-x-1/2 flex-col gap-2 rounded-4 border bg-surface-base px-3 py-2 shadow-sm"
			:class="paused ? 'border-outline-amber-3' : 'pointer-events-none border-outline-gray-2'"
			:style="{ left: `${width / 2}px` }"
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
			{{ __("Drag to rotate · Shift + drag to move · Scroll to zoom") }}
		</p>
	</div>
</template>
