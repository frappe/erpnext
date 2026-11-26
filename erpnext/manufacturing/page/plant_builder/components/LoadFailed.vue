<script setup>
import { Button } from "frappe-ui";
import { __ } from "../lib/api";

const emit = defineEmits(["retry"]);
</script>

<template>
	<div class="flex flex-1 flex-col items-center justify-center gap-3 p-10 text-center">
		<span class="lucide-cloud-off size-6 text-ink-gray-5" aria-hidden="true" />
		<p class="text-base-semibold text-ink-gray-8">{{ __("This page could not be loaded") }}</p>
		<Button icon-left="lucide-refresh-cw" :label="__('Retry')" @click="emit('retry')" />
	</div>
</template>
