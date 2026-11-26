<script setup>
import { computed } from "vue";
import { SWATCH } from "../../lib/machines";
import { useFacing } from "../../lib/scene";

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
	segments: { type: Number, default: null },
});

const px = (n) => `${n}px`;

const count = computed(() => props.segments ?? Math.max(6, Math.min(12, Math.round(props.r / 4))));
const facing = useFacing(() => Array.from({ length: count.value }, (_, i) => (360 / count.value) * i), -0.3);
const strips = computed(() => {
	const n = count.value;
	const w = 2 * props.r * Math.tan(Math.PI / n) + 1;
	return Array.from({ length: n }, (_, i) => {
		const a = (360 / n) * i;
		const shade = 0.3 * (1 - Math.cos(((a - 150) * Math.PI) / 180)) * 0.5;
		return { i, a, w, shadow: `linear-gradient(rgba(17, 17, 17, ${shade}), rgba(17, 17, 17, ${shade}))` };
	}).filter((s) => props.open || facing.value & (1 << s.i));
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
			class="absolute overflow-hidden bg-surface-gray-3"
			:style="{
				left: px(-s.w / 2),
				top: px(-h),
				width: px(s.w),
				height: px(h),
				transformOrigin: 'center bottom',
				transform: `rotateZ(${s.a}deg) translateY(${r}px) rotateX(-90deg)`,
				backgroundImage: s.shadow,
			}"
		>
			<div
				v-if="level > 0"
				class="absolute inset-x-0 bottom-0"
				:class="fill"
				:style="{ height: `${level}%`, backgroundImage: s.shadow }"
			/>
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
