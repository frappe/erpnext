<script setup>
import { computed, ref } from "vue";
import { useElementSize } from "@vueuse/core";
import { Button, TabButtons, Tooltip } from "frappe-ui";
import MachineModel from "../three/MachineModel.vue";
import PanButtons from "../three/PanButtons.vue";
import { shapeExtent } from "../../lib/machines";
import { useOrbitCamera } from "../../lib/scene";
import { useClock } from "../../lib/clock";
import { __ } from "../../lib/api";
import { clamp } from "../../lib/format";

const props = defineProps({
	machineModel: String,
	shapes: Array,
	selected: { type: Number, default: null },
	running: Boolean,
});

const FLOOR = 480;
const CENTRE = FLOOR / 2;

const stage = ref(null);
const { viewName, rot, tilt, zoom, pan, dragging, setView, fit, zoomBy, panBy, onWheel, onDown } =
	useOrbitCamera();

const { width, height } = useElementSize(stage);
useClock(stage);

const scale = computed(() => clamp(Math.min(width.value, height.value) / 760, 0.4, 2) * zoom.value);
const floorStyle = computed(() => ({
	left: `${width.value / 2 + pan.value.x}px`,
	top: `${height.value / 2 + 40 + pan.value.y}px`,
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
</script>

<template>
	<div class="absolute inset-0 overflow-hidden">
		<div
			ref="stage"
			class="absolute inset-0 select-none"
			:class="dragging ? 'cursor-grabbing' : 'cursor-grab'"
			:style="{ perspective: '2200px', touchAction: 'none' }"
			@pointerdown="onDown"
			@contextmenu.prevent
			@wheel.prevent="onWheel"
		>
			<div class="absolute rounded-5 border border-outline-gray-3 bg-surface-base" :style="floorStyle">
				<div class="pointer-events-none absolute inset-0 rounded-5 text-ink-gray-2" :style="grid" />
				<div class="absolute inset-y-0 w-px bg-surface-gray-4" :style="{ left: `${CENTRE}px` }" />
				<div class="absolute inset-x-0 h-px bg-surface-gray-4" :style="{ top: `${CENTRE}px` }" />
				<MachineModel
					:machine-model="machineModel"
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
					{ label: __('3D'), value: '3d' },
					{ label: __('Top'), value: 'top' },
					{ label: __('Front'), value: 'front' },
				]"
				@update:model-value="setView"
			/>
			<div
				class="flex items-center gap-0.5 rounded-4 border border-outline-gray-2 bg-surface-base p-0.5"
			>
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
				<Tooltip :text="__('Fit machine')"
					><Button variant="ghost" :aria-label="__('Fit machine')" icon="lucide-scan" @click="fit"
				/></Tooltip>
			</div>
			<PanButtons :pan-by="panBy" />
		</div>

		<p class="pointer-events-none absolute bottom-3 left-3 text-xs text-ink-gray-5">
			{{ __("Drag to rotate · Shift + drag to move · Scroll to zoom") }}
		</p>
	</div>
</template>
