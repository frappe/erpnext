<script setup>
defineProps({ title: String, description: String });
</script>

<template>
	<div class="flex items-start gap-3">
		<div class="min-w-0 flex-1">
			<h2 class="text-lg-semibold text-ink-gray-8">{{ title }}</h2>
			<p v-if="description" class="mt-0.5 text-p-sm text-ink-gray-5">{{ description }}</p>
		</div>
		<slot />
	</div>
</template>
