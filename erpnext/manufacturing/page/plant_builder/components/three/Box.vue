<script setup>
import { computed } from "vue";
import { useFacing } from "../../lib/scene";

const props = defineProps({
	x: { type: Number, default: 0 },
	y: { type: Number, default: 0 },
	z: { type: Number, default: 0 },
	w: { type: Number, default: 10 },
	d: { type: Number, default: 10 },
	h: { type: Number, default: 10 },
	tone: { type: String, default: "steel" },
});

const face = (top, side, front, edge) => ({ top, side, front, edge });

const TONES = {
	steel: face("bg-surface-gray-2", "bg-surface-gray-4", "bg-surface-gray-3", "border-outline-gray-4"),
	dark: face("bg-surface-gray-6", "bg-surface-gray-7", "bg-surface-gray-6", "border-outline-gray-7"),
	belt: face("bg-surface-gray-7", "bg-surface-gray-4", "bg-surface-gray-3", "border-outline-gray-5"),
	wood: face("bg-surface-amber-3", "bg-surface-amber-4", "bg-surface-amber-3", "border-outline-amber-4"),
	carton: face("bg-surface-amber-2", "bg-surface-amber-3", "bg-surface-amber-2", "border-outline-amber-4"),
	crate: face("bg-surface-blue-2", "bg-surface-blue-3", "bg-surface-blue-2", "border-outline-blue-3"),
	plate: face("bg-surface-blue-1", "bg-surface-blue-2", "bg-surface-blue-1", "border-outline-blue-3"),
	glass: face("bg-surface-gray-1", "bg-surface-gray-2", "bg-surface-gray-1", "border-outline-gray-4"),
	sack: face("bg-surface-gray-1", "bg-surface-gray-2", "bg-surface-gray-1", "border-outline-gray-3"),
	go: face("bg-surface-green-5", "bg-surface-green-6", "bg-surface-green-5", "border-outline-green-5"),
	godim: face("bg-surface-green-2", "bg-surface-green-3", "bg-surface-green-2", "border-outline-green-3"),
	hold: face("bg-surface-amber-4", "bg-surface-amber-5", "bg-surface-amber-4", "border-outline-amber-5"),
	off: face("bg-surface-gray-3", "bg-surface-gray-4", "bg-surface-gray-3", "border-outline-gray-4"),
	down: face("bg-surface-red-5", "bg-surface-red-6", "bg-surface-red-5", "border-outline-red-5"),
	downdim: face("bg-surface-red-2", "bg-surface-red-3", "bg-surface-red-2", "border-outline-red-3"),
	red: face("bg-surface-red-5", "bg-surface-red-6", "bg-surface-red-5", "border-outline-red-5"),
	amber: face("bg-surface-amber-4", "bg-surface-amber-5", "bg-surface-amber-4", "border-outline-amber-5"),
	cream: face("bg-surface-amber-2", "bg-surface-amber-3", "bg-surface-amber-2", "border-outline-amber-3"),
	blue: face("bg-surface-blue-3", "bg-surface-blue-4", "bg-surface-blue-3", "border-outline-blue-4"),
	green: face("bg-surface-green-4", "bg-surface-green-5", "bg-surface-green-4", "border-outline-green-5"),
	violet: face(
		"bg-surface-violet-4",
		"bg-surface-violet-5",
		"bg-surface-violet-4",
		"border-outline-violet-5"
	),
	gray: face("bg-surface-gray-4", "bg-surface-gray-5", "bg-surface-gray-4", "border-outline-gray-5"),
};

const t = computed(() => TONES[props.tone] ?? TONES.steel);
const facing = useFacing([90, -90, 180, 0], -0.2);
const px = (n) => `${n}px`;
</script>

<template>
	<div
		class="absolute"
		:style="{
			left: px(x),
			top: px(y),
			width: px(w),
			height: px(d),
			transform: `translateZ(${z}px)`,
			transformStyle: 'preserve-3d',
		}"
	>
		<div
			class="absolute inset-0 border"
			:class="[t.top, t.edge]"
			:style="{ transform: `translateZ(${h}px)` }"
		/>
		<div
			v-if="facing & 1"
			class="absolute left-0 top-0 border"
			:class="[t.side, t.edge]"
			:style="{
				width: px(h),
				height: px(d),
				transformOrigin: 'left center',
				transform: 'rotateY(-90deg)',
			}"
		/>
		<div
			v-if="facing & 2"
			class="absolute top-0 border"
			:class="[t.side, t.edge]"
			:style="{
				left: px(w),
				width: px(h),
				height: px(d),
				transformOrigin: 'left center',
				transform: 'rotateY(-90deg)',
			}"
		/>
		<div
			v-if="facing & 4"
			class="absolute left-0 border"
			:class="[t.side, t.edge]"
			:style="{
				top: px(-h),
				width: px(w),
				height: px(h),
				transformOrigin: 'center bottom',
				transform: 'rotateX(-90deg)',
			}"
		/>
		<div
			v-if="facing & 8"
			class="absolute left-0 border"
			:class="[t.front, t.edge]"
			:style="{
				top: px(d - h),
				width: px(w),
				height: px(h),
				transformOrigin: 'center bottom',
				transform: 'rotateX(-90deg)',
			}"
		/>
	</div>
</template>
