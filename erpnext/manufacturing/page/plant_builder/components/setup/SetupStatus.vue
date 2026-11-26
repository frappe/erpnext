<script setup>
import { __ } from "../../lib/api";

defineProps({ errors: { type: Array, default: () => [] } });
</script>

<template>
	<div v-if="errors.length" class="rounded-5 border border-outline-red-2 bg-surface-red-1 p-3">
		<div class="flex items-center gap-2">
			<span class="lucide-circle-alert size-4 text-ink-red-5" aria-hidden="true" />
			<p class="text-base font-medium text-ink-gray-8">
				{{
					errors.length === 1
						? __("1 thing to fix before creating BOMs")
						: __("{0} things to fix before creating BOMs", [errors.length])
				}}
			</p>
		</div>
		<ul class="mt-2 space-y-1 pl-6">
			<li v-for="error in errors" :key="error" class="list-disc text-p-sm text-ink-red-5">
				{{ error }}
			</li>
		</ul>
	</div>
</template>
