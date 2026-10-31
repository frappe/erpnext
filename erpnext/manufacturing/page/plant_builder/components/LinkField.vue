<script setup>
import { computed, ref, watch } from "vue";
import { Combobox, FormLabel } from "frappe-ui";

const props = defineProps({
	modelValue: { type: String, default: "" },
	doctype: { type: String, required: true },
	label: { type: String, default: "" },
	filters: { type: Object, default: () => ({}) },
	placeholder: { type: String, default: "" },
	description: { type: String, default: "" },
	size: { type: String, default: "sm" },
	disabled: Boolean,
});
const emit = defineEmits(["update:modelValue", "select"]);

const query = ref("");
const results = ref([]);
const loading = ref(false);
let requestId = 0;

async function search(text) {
	const id = ++requestId;
	loading.value = true;
	const rows = await window.frappe.xcall("frappe.desk.search.search_link", {
		doctype: props.doctype,
		txt: text || "",
		filters: props.filters,
		page_length: 20,
	});
	if (id !== requestId) return;
	results.value = rows || [];
	loading.value = false;
}

watch(query, (text) => search(text));

const options = computed(() => {
	const rows = results.value.map((row) => ({
		label: row.label || row.value,
		value: row.value,
		description: row.description && row.description !== row.value ? row.description : undefined,
	}));
	if (props.modelValue && !rows.some((row) => row.value === props.modelValue)) {
		rows.unshift({ label: props.modelValue, value: props.modelValue });
	}
	return rows;
});

function onOpen(open) {
	if (!open) return;
	query.value = "";
	search("");
}

function onSelect(value) {
	emit("update:modelValue", value || "");
	emit("select", value || "");
}
</script>

<template>
	<div class="space-y-1.5">
		<FormLabel v-if="label" :label="label" />
		<Combobox
			:model-value="modelValue || null"
			v-model:query="query"
			:options="options"
			:filterable="false"
			:loading="loading"
			:placeholder="placeholder"
			:size="size"
			:disabled="disabled"
			class="w-full"
			@update:model-value="onSelect"
			@update:open="onOpen"
		/>
		<p v-if="description" class="text-p-xs text-ink-gray-5">{{ description }}</p>
	</div>
</template>
