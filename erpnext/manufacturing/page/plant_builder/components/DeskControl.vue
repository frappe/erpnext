<script setup>
import { inject, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { FormLabel } from "frappe-ui";
import { READ_ONLY } from "../lib/plant";

const props = defineProps({
	modelValue: { type: String, default: "" },
	fieldtype: { type: String, default: "Link" },
	options: { type: [String, Array], required: true },
	label: { type: String, default: "" },
	filters: { type: Object, default: () => ({}) },
	description: { type: String, default: "" },
	disabled: Boolean,
});
const emit = defineEmits(["update:modelValue"]);

const host = ref(null);
let control = null;
let parent = null;

function makeSlottedParent() {
	const name = `desk-control-${window.frappe.utils.get_random(10)}`;
	const slot = document.createElement("slot");
	slot.name = name;
	host.value.append(slot);

	const element = document.createElement("div");
	element.slot = name;
	host.value.getRootNode().host.append(element);
	return element;
}

function onChange() {
	const value = control.get_value() || "";
	if (value !== (props.modelValue || "")) emit("update:modelValue", value);
}

const readOnly = inject(READ_ONLY, ref(false));

onMounted(() => {
	parent = makeSlottedParent();
	control = window.frappe.ui.form.make_control({
		parent,
		df: {
			fieldtype: props.fieldtype,
			options: props.options,
			read_only: props.disabled || readOnly.value ? 1 : 0,
			get_query: () => ({ filters: props.filters }),
			change: onChange,
		},
		render_input: true,
		only_input: true,
		with_link_btn: props.fieldtype === "Link",
	});
	control.$wrapper.css("margin-bottom", 0);
	control.set_input(props.modelValue || "");
});

onBeforeUnmount(() => parent?.remove());

watch(
	() => props.modelValue,
	(value) => {
		if (control && (control.get_value() || "") !== (value || "")) control.set_input(value || "");
	}
);

watch(
	() => JSON.stringify(props.options),
	() => {
		control.df.options = props.options;
		control.refresh();
		control.set_input(props.modelValue || "");
	}
);

watch(
	() => props.disabled,
	(disabled) => {
		control.df.read_only = disabled ? 1 : 0;
		control.refresh();
	}
);
</script>

<template>
	<div class="space-y-1.5">
		<FormLabel v-if="label" :label="label" />
		<div ref="host" class="w-full" />
		<p v-if="description" class="text-p-xs text-ink-gray-5">{{ description }}</p>
	</div>
</template>
