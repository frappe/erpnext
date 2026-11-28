<script setup>
import { Button, TextInput } from "frappe-ui";
import { __ } from "../../lib/api";
import { num } from "../../lib/format";

const model = defineModel();
const props = defineProps({
	step: { type: Number, default: 1 },
	label: String,
	invalid: Boolean,
	disabled: Boolean,
});

const bump = (direction) => (model.value = Math.max(0, num(model.value) + direction * props.step));
</script>

<template>
	<div class="flex items-center gap-1.5">
		<Button
			size="lg"
			icon="lucide-minus"
			:aria-label="__('Less {0}', [label])"
			:disabled="disabled"
			@click="bump(-1)"
		/>
		<TextInput
			v-model="model"
			type="number"
			size="lg"
			:aria-label="label"
			:disabled="disabled"
			class="w-28 [&_input]:text-right [&_input]:tabular-nums"
			:class="invalid ? '[&_input]:text-ink-red-5' : ''"
		/>
		<Button
			size="lg"
			icon="lucide-plus"
			:aria-label="__('More {0}', [label])"
			:disabled="disabled"
			@click="bump(1)"
		/>
	</div>
</template>
