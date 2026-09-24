<template>
	<div class="flex flex-col gap-3 p-6">
		<h1 class="text-xl font-semibold text-ink-gray-9">Replacement page from ERPNext</h1>
		<p class="text-base text-ink-gray-7">doctype: {{ doctype }}</p>
		<p class="text-base text-ink-gray-7">name: {{ name ?? "(none)" }}</p>
		<RouterLink
			class="text-base text-ink-gray-9 underline"
			:to="routeFor(doctype, name, { standard: true })"
		>
			Open the standard page
		</RouterLink>
	</div>
</template>

<script setup>
import { routeFor } from "@shell";

defineProps({
	doctype: { type: String, required: true },
	name: { type: String, default: null },
});
</script>
