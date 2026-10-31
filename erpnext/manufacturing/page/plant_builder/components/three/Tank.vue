<script setup>
import { computed } from "vue";
import { SWATCH } from "../../lib/machines";

const props = defineProps({
	x: Number,
	y: Number,
	z: { type: Number, default: 0 },
	r: Number,
	h: Number,
	level: { type: Number, default: 0 },
	liquid: { type: String, default: "red" },
	open: Boolean,
	active: Boolean,
	bare: Boolean,
	segments: { type: Number, default: 18 },
});

const px = (n) => `${n}px`;

const strips = computed(() => {
	const n = props.segments;
	const w = 2 * props.r * Math.tan(Math.PI / n) + 1;
	return Array.from({ length: n }, (_, i) => {
		const a = (360 / n) * i;
		const shade = 0.3 * (1 - Math.cos(((a - 150) * Math.PI) / 180)) * 0.5;
		return { i, a, w, shade };
	});
});

const fill = computed(() => SWATCH[props.liquid] ?? SWATCH.gray);
const disk = computed(() => ({
	left: px(-props.r),
	top: px(-props.r),
	width: px(2 * props.r),
	height: px(2 * props.r),
}));
const surfaceZ = computed(() => Math.max(1, (props.level / 100) * props.h));
</script>

<template>
	<div
		class="absolute"
		:style="{
			left: px(x),
			top: px(y),
			width: 0,
			height: 0,
			transform: `translateZ(${z}px)`,
			transformStyle: 'preserve-3d',
		}"
	>
		<div v-if="!bare" class="absolute rounded-full bg-surface-gray-3" :style="disk" />
		<div
			v-for="s in strips"
			:key="s.i"
			class="absolute left-0 top-0"
			:style="{ transform: `rotateZ(${s.a}deg) translateY(${r}px)`, transformStyle: 'preserve-3d' }"
		>
			<div
				class="absolute overflow-hidden bg-surface-gray-3"
				:style="{
					left: px(-s.w / 2),
					top: px(-h),
					width: px(s.w),
					height: px(h),
					transformOrigin: 'center bottom',
					transform: 'rotateX(-90deg)',
				}"
			>
				<div class="absolute inset-x-0 bottom-0" :class="fill" :style="{ height: `${level}%` }" />
				<div class="absolute inset-0 bg-surface-gray-9" :style="{ opacity: s.shade }" />
			</div>
		</div>
		<div
			v-if="open && level > 0"
			class="absolute rounded-full"
			:class="fill"
			:style="{ ...disk, transform: `translateZ(${surfaceZ}px)` }"
		/>
		<div
			v-if="!bare"
			class="absolute rounded-full"
			:class="[
				open ? 'border-[6px] bg-transparent' : 'border bg-surface-gray-2',
				active ? 'border-outline-gray-7' : 'border-outline-gray-4',
			]"
			:style="{ ...disk, transform: `translateZ(${h}px)` }"
		/>
	</div>
</template>
