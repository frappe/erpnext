<script setup>
import { Button } from "frappe-ui";

defineProps({
	// a full class such as "lucide-wallet", or the build leaves the icon out
	icon: { type: String, required: true },
	title: { type: String, required: true },
	description: { type: String, default: "" },
	actions: { type: Array, default: () => [] },
});
</script>

<template>
	<div class="flex flex-col items-center justify-center gap-2 py-10 text-center">
		<div class="mb-1 rounded-full bg-surface-gray-2 p-3 text-ink-gray-5">
			<span :class="icon" class="block size-5" aria-hidden="true" />
		</div>
		<p class="text-base font-medium text-ink-gray-8">{{ title }}</p>
		<p v-if="description" class="max-w-md text-p-sm text-ink-gray-5">{{ description }}</p>
		<div v-if="actions.length" class="mt-2 flex flex-wrap justify-center gap-2">
			<Button
				v-for="action in actions"
				:key="action.label"
				:label="action.label"
				:icon-left="action.icon"
				@click="action.onClick"
			/>
		</div>
	</div>
</template>
