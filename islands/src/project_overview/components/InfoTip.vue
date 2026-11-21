<script setup>
import { Tooltip } from "frappe-ui";

defineProps({
	text: { type: String, required: true },
});
</script>

<template>
	<Tooltip :hover-delay="100">
		<template #content>
			<div class="max-w-xs whitespace-pre-line text-start">{{ text }}</div>
		</template>
		<span
			class="lucide-info ml-1 inline-block size-3.5 cursor-help align-middle text-ink-gray-4"
			role="img"
			:aria-label="text"
		/>
	</Tooltip>
</template>
