<script setup>
import { computed, ref } from "vue";
import { useElementSize, useEventListener } from "@vueuse/core";
import { Button, TabButtons, Tooltip } from "frappe-ui";
import MachineModel from "../../plant_builder/components/three/MachineModel.vue";
import PackLine from "../../plant_builder/components/three/PackLine.vue";
import { useClock } from "../../plant_builder/lib/clock";
import { __, go } from "../lib/api";
import { buildLayout } from "../lib/layout";
import { STATION_DOT, machineMode, stationSummary } from "../lib/status";

const props = defineProps({
	lines: Array,
	highlight: { type: Array, default: () => [] },
	allowed: { type: Array, default: null },
});

const PERSPECTIVE = 2200;
const PRESETS = { "3d": [-12, 50], top: [0, 0], front: [0, 72] };
const layout = computed(() => buildLayout(props.lines));
const viewName = ref("3d");
const rot = ref(-12);
const tilt = ref(50);
const zoom = ref(1);
const dragging = ref(false);
const stage = ref(null);
const orbit = { on: false, x: 0, y: 0, moved: 0 };
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

useClock(stage);
const { width, height } = useElementSize(stage);
const fit = computed(() =>
	width.value
		? clamp(
				Math.min((width.value - 40) / layout.value.W, (height.value - 60) / (layout.value.H * 0.7)),
				0.15,
				1.6
		  )
		: 0.5
);
const scale = computed(() => fit.value * zoom.value * (1 - tilt.value / 400));
const center = computed(() => ({ x: width.value / 2, y: height.value / 2 + 10 }));

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

function setView(name) {
	viewName.value = name;
	animateTo(...PRESETS[name]);
}

function onDown(event) {
	if (event.button === 0) Object.assign(orbit, { on: true, x: event.clientX, y: event.clientY, moved: 0 });
}

useEventListener(window, "pointermove", (event) => {
	if (!orbit.on) return;
	const dx = event.clientX - orbit.x;
	const dy = event.clientY - orbit.y;
	orbit.moved += Math.abs(dx) + Math.abs(dy);
	dragging.value = orbit.moved > 4;
	rot.value += dx * 0.35;
	tilt.value = clamp(tilt.value - dy * 0.3, 0, 80);
	Object.assign(orbit, { x: event.clientX, y: event.clientY });
});
useEventListener(window, "pointerup", () => {
	orbit.on = false;
	dragging.value = false;
});

function project(point) {
	const r = (rot.value * Math.PI) / 180;
	const a = (tilt.value * Math.PI) / 180;
	const x0 = point.x - layout.value.W / 2;
	const y0 = point.y - layout.value.H / 2;
	const x1 = x0 * Math.cos(r) - y0 * Math.sin(r);
	const y1 = x0 * Math.sin(r) + y0 * Math.cos(r);
	const y2 = y1 * Math.cos(a) - point.z * Math.sin(a);
	const z2 = y1 * Math.sin(a) + point.z * Math.cos(a);
	const f = PERSPECTIVE / (PERSPECTIVE - z2);
	return {
		left: `${center.value.x + scale.value * x1 * f}px`,
		top: `${center.value.y + scale.value * y2 * f}px`,
	};
}

const isOpen = (name) => !props.allowed || props.allowed.includes(name);
const tags = computed(() =>
	width.value
		? layout.value.rows.flatMap((row) =>
				row.cells.map((cell) => {
					const open = isOpen(cell.row.name);
					const detailed =
						scale.value > 0.75 ||
						props.highlight.includes(cell.row.name) ||
						cell.row.status === "Problem";
					return {
						name: cell.row.name,
						status: cell.row.status,
						open,
						mine: props.highlight.includes(cell.row.name),
						summary: open && detailed ? stationSummary(cell.row) : null,
						style: project({ x: cell.x, y: cell.y, z: cell.tagZ }),
					};
				})
		  )
		: []
);

const zoneClass = (row) => {
	if (row.status === "Problem") return "border-2 border-outline-red-4 bg-surface-red-1";
	if (props.highlight.includes(row.name)) return "border-2 border-outline-gray-7 bg-surface-gray-2";
	return "border border-dashed border-outline-gray-4";
};

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
const LEGEND = [
	["Production", "Running"],
	["Maintenance", "Maintenance"],
	["Problem", "Down"],
	["Idle", "Idle"],
];
</script>

<template>
	<div class="relative overflow-hidden rounded-6 border border-outline-gray-2 bg-surface-gray-1">
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
			@wheel.prevent="(event) => (zoom = clamp(zoom - event.deltaY * 0.0015, 0.5, 3))"
		>
			<div class="absolute rounded-5 border border-outline-gray-3 bg-surface-base" :style="floorStyle">
				<div class="pointer-events-none absolute inset-0 rounded-5 text-ink-gray-2" :style="grid" />
				<template v-for="row in layout.rows" :key="row.line.name">
					<div
						class="pointer-events-none absolute flex items-center rounded-5 bg-surface-gray-2 px-4"
						:style="{
							left: `${row.label.x}px`,
							top: `${row.label.y}px`,
							width: `${row.label.w}px`,
							height: '100px',
						}"
					>
						<span class="text-[30px] font-semibold leading-tight text-ink-gray-7">{{
							row.line.name || __("Other workstations")
						}}</span>
					</div>
					<template v-for="cell in row.cells" :key="cell.row.name">
						<div
							class="pointer-events-none absolute rounded-5"
							:class="zoneClass(cell.row)"
							:style="{
								left: `${cell.zone.x}px`,
								top: `${cell.zone.y}px`,
								width: `${cell.zone.w}px`,
								height: `${cell.zone.h}px`,
							}"
						/>
						<PackLine
							v-if="cell.pack"
							:machine-model="cell.row.machine_model"
							:x0="cell.zone.x"
							:yc="cell.y"
							:level="cell.row.current ? 60 : 0"
							color="blue"
							:mode="machineMode(cell.row)"
							:working="machineMode(cell.row) === 'run'"
							:active="highlight.includes(cell.row.name)"
						/>
						<MachineModel
							v-else
							:machine-model="cell.row.machine_model"
							:shapes="cell.row.shapes"
							:x="cell.x"
							:y="cell.y"
							:level="cell.row.current ? 60 : 0"
							color="blue"
							:mode="machineMode(cell.row)"
							:working="machineMode(cell.row) === 'run'"
							:active="highlight.includes(cell.row.name)"
							:rot="rot"
							:tilt="tilt"
						/>
					</template>
				</template>
			</div>
		</div>

		<component
			:is="tag.open ? 'button' : 'div'"
			v-for="tag in tags"
			:key="tag.name"
			:type="tag.open ? 'button' : undefined"
			class="absolute flex h-8 max-w-[16rem] -translate-x-1/2 -translate-y-full items-center gap-1.5 rounded-4 border bg-surface-base px-2.5 shadow-sm"
			:class="[
				tag.mine ? 'border-outline-gray-7' : 'border-outline-gray-2',
				tag.open ? 'hover:bg-surface-gray-2' : '',
			]"
			:style="tag.style"
			@click="tag.open && go('station', tag.name)"
		>
			<span
				class="size-2 shrink-0 rounded-full"
				:class="STATION_DOT[tag.status] || 'bg-surface-gray-5'"
				aria-hidden="true"
			/>
			<span class="shrink-0 text-sm font-medium text-ink-gray-8">{{ tag.name }}</span>
			<span v-if="tag.summary" class="min-w-0 truncate text-xs" :class="tag.summary.tone">{{
				tag.summary.text
			}}</span>
			<span v-else-if="!tag.open" class="text-xs text-ink-gray-5">{{ __(tag.status) }}</span>
		</component>

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
					><Button
						variant="ghost"
						icon="lucide-rotate-ccw"
						:aria-label="__('Rotate left')"
						@click="animateTo(rot - 45, tilt)"
				/></Tooltip>
				<Tooltip :text="__('Rotate right')"
					><Button
						variant="ghost"
						icon="lucide-rotate-cw"
						:aria-label="__('Rotate right')"
						@click="animateTo(rot + 45, tilt)"
				/></Tooltip>
				<Tooltip :text="__('Zoom out')"
					><Button
						variant="ghost"
						icon="lucide-zoom-out"
						:aria-label="__('Zoom out')"
						@click="zoom = clamp(zoom - 0.2, 0.5, 3)"
				/></Tooltip>
				<Tooltip :text="__('Zoom in')"
					><Button
						variant="ghost"
						icon="lucide-zoom-in"
						:aria-label="__('Zoom in')"
						@click="zoom = clamp(zoom + 0.2, 0.5, 3)"
				/></Tooltip>
			</div>
		</div>

		<div
			class="absolute bottom-3 left-3 flex flex-wrap items-center gap-3 rounded-4 border border-outline-gray-2 bg-surface-base px-3 py-1.5 text-xs text-ink-gray-6"
		>
			<span v-for="[status, label] in LEGEND" :key="status" class="flex items-center gap-1.5">
				<span class="size-2 rounded-full" :class="STATION_DOT[status]" aria-hidden="true" />{{
					__(label)
				}}
			</span>
			<span>{{ __("Drag to rotate · Scroll to zoom") }}</span>
		</div>
	</div>
</template>
