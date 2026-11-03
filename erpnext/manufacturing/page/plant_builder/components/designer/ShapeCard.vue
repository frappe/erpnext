<script setup>
import { computed } from "vue";
import { Button, Checkbox, TextInput, Tooltip } from "frappe-ui";
import DeskControl from "../DeskControl.vue";
import { __ } from "../../lib/api";
import { SHAPES } from "../../lib/machines";

const props = defineProps({
	shape: Object,
	index: Number,
	selected: Boolean,
	disabled: Boolean,
});
const emit = defineEmits(["select", "duplicate", "remove"]);

const SHAPE_NAMES = Object.keys(SHAPES);
const FINISHES = [
	"Steel",
	"Dark",
	"Plate",
	"Product",
	"Heat",
	"Red",
	"Amber",
	"Cream",
	"Blue",
	"Green",
	"Violet",
	"Gray",
];
const LABELS = { x: "X", y: "Y", z: "Z", width: "Width", depth: "Depth", radius: "Radius", height: "Height" };
const TANKS = ["Tank", "Open Tank"];

const spec = computed(() => SHAPES[props.shape.shape] || { size: {} });
const numbers = computed(() => {
	const fields = ["x", "y", "z", ...Object.keys(spec.value.size)];
	return [...fields, ...Array(6 - fields.length).fill(null)];
});
const checks = computed(() => [
	...(TANKS.includes(props.shape.shape) ? [["shows_level", __("Show Batch Level")]] : []),
	...(props.shape.shape === "Steam" ? [["is_small", __("Small")]] : []),
	["shakes", __("Shake While Working")],
]);

function setShape(name) {
	const next = SHAPES[name];
	Object.entries(next.size).forEach(([field, value]) => {
		if (!props.shape[field]) props.shape[field] = value;
	});
	const finish = props.shape.finish;
	if (next.finish && (!finish || finish === SHAPES[props.shape.shape]?.finish))
		props.shape.finish = next.finish;
	props.shape.shape = name;
}
</script>

<template>
	<div
		class="rounded-5 border bg-surface-base"
		:class="selected ? 'border-outline-gray-5' : 'border-outline-gray-2'"
		@focusin="emit('select')"
		@pointerdown="emit('select')"
	>
		<div class="flex h-12 items-center gap-2 border-b border-outline-gray-1 px-3">
			<span
				class="flex size-6 shrink-0 items-center justify-center rounded-full border border-outline-gray-3 text-xs tabular-nums text-ink-gray-6"
			>
				{{ index + 1 }}
			</span>
			<div class="w-40 shrink-0">
				<DeskControl
					fieldtype="Select"
					:options="SHAPE_NAMES"
					:model-value="shape.shape"
					:disabled="disabled"
					@update:model-value="setShape"
				/>
			</div>
			<div class="w-32 shrink-0">
				<DeskControl
					v-if="spec.finish"
					v-model="shape.finish"
					fieldtype="Select"
					:options="FINISHES"
					:disabled="disabled"
				/>
			</div>
			<div class="flex-1" />
			<template v-if="!disabled">
				<Tooltip :text="__('Duplicate')">
					<Button variant="ghost" icon="lucide-copy" @click="emit('duplicate')" />
				</Tooltip>
				<Tooltip :text="__('Remove')">
					<Button variant="ghost" icon="lucide-x" @click="emit('remove')" />
				</Tooltip>
			</template>
		</div>
		<div class="grid grid-cols-6 gap-2 px-3 pt-2">
			<div v-for="(field, i) in numbers" :key="field || `slot${i}`" class="min-w-0">
				<template v-if="field">
					<p class="mb-1 truncate text-right text-xs text-ink-gray-5">{{ __(LABELS[field]) }}</p>
					<TextInput
						v-model.number="shape[field]"
						type="number"
						class="[&_input]:text-right [&_input]:[appearance:textfield] [&_input::-webkit-inner-spin-button]:appearance-none"
						:disabled="disabled"
					/>
				</template>
			</div>
		</div>
		<div class="flex h-10 items-center gap-5 px-3">
			<Checkbox
				v-for="[field, label] in checks"
				:key="field"
				:label="label"
				:model-value="!!shape[field]"
				:disabled="disabled"
				@update:model-value="shape[field] = $event ? 1 : 0"
			/>
		</div>
	</div>
</template>
